"""Experimental single-SITL backend for the existing wildlife UAV behavior.

PX4 owns position, attitude, rates and motors. This node reuses the V0.2
mission FSM, replacing its coordinate integration with measured telemetry and
position intent. Do not launch uav_node for the same drone alongside it.
"""
import math
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import (VehicleLocalPosition, VehicleStatus, VehicleLandDetected,
                          VehicleCommand, VehicleCommandAck, OffboardControlMode,
                          TrajectorySetpoint, BatteryStatus)
from wildlife_interfaces.msg import DroneCommand, DroneState
from std_msgs.msg import Bool
from wildlife_vehicles.uav_node import UAVNode


def enu_to_ned(position):
    x, y, z = position
    return [float(y), float(x), float(-z)]


def ned_to_enu(position):
    x, y, z = position
    return float(y), float(x), float(-z)


def versioned_topic(prefix, direction, name, message_type):
    version = getattr(message_type, 'MESSAGE_VERSION', 0)
    suffix = f'_v{version}' if version else ''
    return f'{prefix}/fmu/{direction}/{name}{suffix}'


class PX4UAVAdapter(UAVNode):
    def __init__(self):
        super().__init__()
        for key, value in {'sitl_enabled': False, 'px4_namespace': '', 'system_id': 1,
                           'telemetry_timeout': 1.0, 'status_land_timeout_s': 0.0, 'max_horizontal_distance': 60.0,
                           'max_altitude': 30.0, 'search_half_height': 30.0,
                           'map_origin_x': 0.0, 'map_origin_y': 0.0, 'map_origin_z': 0.0}.items():
            self.declare_parameter(key, value)
        if not self.get_parameter('sitl_enabled').value:
            raise RuntimeError('This experimental backend requires sitl_enabled:=true')
        self.system_id = int(self.get_parameter('system_id').value)
        if self.id != f'uav{self.system_id:02d}' or not 1 <= self.system_id <= 8:
            raise ValueError('drone_id must match PX4 system_id in 1..8')
        self.prefix = str(self.get_parameter('px4_namespace').value).rstrip('/')
        self.status = self.local = self.land = None
        self.received = {}
        self.goal = None
        self.stream_start = None
        self.last_commands = {}
        self.command_attempts = {}
        self.acks = {}
        self.fault = None
        self.was_airborne = False
        self.was_offboard = False
        self.battery = -1.0
        self.reset_counters = None
        self.yaw = 0.0
        self.search_goal = None
        self.next_lane = 0.0
        self.origin = tuple(float(self.get_parameter(f'map_origin_{axis}').value) for axis in 'xyz')
        self.home_z = 0.0
        self.pending_launch = False
        self.ready_pub = self.create_publisher(Bool, f'/drones/{self.id}/ready', 10)
        self.heartbeat_pub = self.create_publisher(OffboardControlMode, self.topic('in', 'offboard_control_mode', OffboardControlMode), 10)
        self.setpoint_pub = self.create_publisher(TrajectorySetpoint, self.topic('in', 'trajectory_setpoint', TrajectorySetpoint), 10)
        self.command_pub = self.create_publisher(VehicleCommand, self.topic('in', 'vehicle_command', VehicleCommand), 10)
        for name, msg_type, callback in [
                ('vehicle_local_position', VehicleLocalPosition, self.local_cb),
                ('vehicle_status', VehicleStatus, self.status_cb),
                ('vehicle_land_detected', VehicleLandDetected, self.land_cb),
                ('vehicle_command_ack', VehicleCommandAck, self.ack_cb),
                ('battery_status', BatteryStatus, self.battery_cb)]:
            self.create_subscription(msg_type, self.topic('out', name, msg_type), callback, qos_profile_sensor_data)
        self.get_logger().info('Single-UAV PX4 backend ready; awaiting telemetry and typed LAUNCH')

    def topic(self, direction, name, msg_type):
        return versioned_topic(self.prefix, direction, name, msg_type)

    def status_cb(self, msg):
        self.status = msg
        self.received['status'] = time.monotonic()

    def land_cb(self, msg):
        self.land = msg
        self.received['land'] = time.monotonic()
        if not msg.landed:
            self.was_airborne = True

    def battery_cb(self, msg):
        if math.isfinite(msg.remaining) and msg.remaining >= 0:
            self.battery = max(0., min(100., float(msg.remaining) * 100.))

    def local_cb(self, msg):
        if not (msg.xy_valid and msg.z_valid and all(math.isfinite(v) for v in (msg.x, msg.y, msg.z, msg.heading))):
            self.received.pop('local', None)
            return
        counters = (msg.xy_reset_counter, msg.z_reset_counter)
        if self.reset_counters is not None and counters != self.reset_counters and self.was_airborne:
            self.fail('PX4 position origin reset in flight; stop external control')
        self.reset_counters = counters
        self.local = msg
        local = ned_to_enu((msg.x, msg.y, msg.z))
        self.x, self.y, self.z = tuple(local[i] + self.origin[i] for i in range(3))
        self.yaw = math.pi / 2 - msg.heading
        self.received['local'] = time.monotonic()

    def fresh(self):
        timeout = float(self.get_parameter('telemetry_timeout').value)
        now = time.monotonic()
        slow_timeout = float(self.get_parameter('status_land_timeout_s').value)
        if slow_timeout <= 0:
            slow_timeout = timeout  # Preserve the existing configured timeout unless explicitly split.
        return (now - self.received.get('local', -math.inf) < timeout
                and all(now - self.received.get(key, -math.inf) < slow_timeout
                        for key in ('status', 'land')))

    def fail(self, reason):
        if self.fault is None:
            self.get_logger().error(reason)
        self.fault = reason
        self.state = DroneState.PAUSED

    def ready(self):
        return (self.fresh() and self.fault is None and self.status.pre_flight_checks_pass
                and self.land.landed and self.state == DroneState.STORED
                and not self.launch_inhibited)

    def command_cb(self, msg):
        if msg.drone_id != self.id:
            return
        if msg.command == DroneCommand.LAUNCH:
            if self.state == DroneState.STORED and not self.launch_inhibited:
                self.pending_launch = True
            return
        if msg.command == DroneCommand.RETURN_HOME:
            self.pending_launch = False
        if self.fault:
            # A fault cannot resume the ROS FSM, including while telemetry is stale.
            if msg.command == DroneCommand.RETURN_HOME and self.fresh():
                self.state = DroneState.RETURNING
                self.send_command(VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
            return
        # Mission overrides latch even when telemetry is not ready.
        if not self.fresh():
            super().command_cb(msg)
            return
        if msg.command == DroneCommand.HOLD_POSITION:
            self.goal = (self.x, self.y, self.z)
        super().command_cb(msg)

    def accept_pending_launch(self):
        if not self.pending_launch or not self.ready():
            return
        self.pending_launch = False
        self.home_x, self.home_y, self.home_z = self.x, self.y, self.z
        self.goal = (self.home_x, self.home_y, self.home_z + self.alt)
        super().command_cb(DroneCommand(drone_id=self.id, command=DroneCommand.LAUNCH))

    def ack_cb(self, msg):
        if (msg.target_system != 255 or msg.target_component != 1
                or msg.command not in self.last_commands):
            return
        self.acks[msg.command] = msg.result
        if msg.result not in (VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
                              VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS,
                              VehicleCommandAck.VEHICLE_CMD_RESULT_TEMPORARILY_REJECTED):
            self.fail(f'PX4 rejected command {msg.command}: result {msg.result}')

    def send_command(self, command, param1=0., param2=0.):
        now = time.monotonic()
        if now - self.last_commands.get(command, -math.inf) < 1.0:
            return
        attempts = self.command_attempts.get(command, 0)
        if attempts >= 10:
            self.fail(f'PX4 command {command} did not reach its requested state')
            return
        msg = VehicleCommand()
        msg.timestamp = self.get_clock().now().nanoseconds // 1000
        msg.command = command
        msg.param1, msg.param2 = float(param1), float(param2)
        msg.target_system = self.system_id
        msg.target_component = 1
        msg.source_system = 255
        msg.source_component = 1
        msg.from_external = True
        self.command_pub.publish(msg)
        self.last_commands[command] = now
        self.command_attempts[command] = attempts + 1

    def stream(self):
        if self.goal is None or self.fault:
            return
        if self.stream_start is None:
            self.stream_start = time.monotonic()
        stamp = self.get_clock().now().nanoseconds // 1000
        mode = OffboardControlMode(timestamp=stamp, position=True)
        goal = TrajectorySetpoint()
        goal.timestamp = stamp
        local_goal = tuple(self.goal[i] - self.origin[i] for i in range(3))
        goal.position = enu_to_ned(local_goal)
        goal.velocity = [math.nan] * 3
        goal.acceleration = [math.nan] * 3
        goal.jerk = [math.nan] * 3
        goal.yaw = math.nan
        goal.yawspeed = math.nan
        self.heartbeat_pub.publish(mode)
        self.setpoint_pub.publish(goal)
        # PX4 requires an established >2 Hz heartbeat before entering Offboard.
        if time.monotonic() - self.stream_start < 1.2:
            return
        if self.status.nav_state != VehicleStatus.NAVIGATION_STATE_OFFBOARD:
            self.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1., 6.)
        elif self.status.arming_state != VehicleStatus.ARMING_STATE_ARMED and not self.was_airborne:
            self.send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.)

    def move_toward(self, tx, ty, tz):
        # Publish intent only; coordinates change exclusively in local_cb.
        if not all(math.isfinite(v) for v in (tx, ty, tz)):
            self.fail('Non-finite position intent')
            return False
        radius = float(self.get_parameter('max_horizontal_distance').value)
        ceiling = float(self.get_parameter('max_altitude').value)
        if math.hypot(tx - self.home_x, ty - self.home_y) > radius or not 0.5 <= tz - self.home_z <= ceiling:
            self.fail('Position intent exceeds the configured SITL envelope')
            return False
        self.goal = (tx, ty, tz)
        return math.dist((self.x, self.y, self.z), self.goal) <= self.tol

    def move_to_standoff(self):
        if not self.target:
            return False
        target = self.target.pose.pose.position
        return self.move_toward(target.x, target.y + self.standoff,
                                self.home_z + self.alt + self.alt_offset)

    def lawnmower_step(self):
        if self.search_goal is None:
            self.search_goal = (self.home_x + self.half_width, self.home_y, self.home_z + self.alt)
        if self.move_toward(*self.search_goal):
            self.next_lane += self.lane
            if self.next_lane > float(self.get_parameter('search_half_height').value):
                self.next_lane = 0.0
            self.lane_dir *= -1.
            self.search_goal = (self.home_x + self.lane_dir*self.half_width,
                                self.home_y + self.next_lane, self.home_z + self.alt)

    def drain_battery(self):
        pass  # BatteryStatus is authoritative; never simulate PX4 battery drain.

    def tick(self):
        if not hasattr(self, 'received'):
            return
        self.ready_pub.publish(Bool(data=self.ready()))
        self.accept_pending_launch()
        if not self.fresh():
            if self.stream_start is not None and self.state != DroneState.DOCKED:
                ages = {key: round(time.monotonic() - self.received.get(key, -math.inf), 2) for key in ('local', 'status', 'land')}
                self.fail(f'Telemetry stale {ages}; heartbeat stopped so PX4 owns failsafe response')
            return
        # A completed landing is terminal even if later transport or preflight
        # health changes. For a faulted return, require fresh measured landing,
        # disarm and proximity to the latched home before logical docking.
        if (self.state == DroneState.PAUSED and self.was_airborne and self.land.landed
                and self.status.arming_state == VehicleStatus.ARMING_STATE_DISARMED
                and math.hypot(self.x - self.home_x, self.y - self.home_y) <= 2.0):
            self.state = DroneState.DOCKED
        if self.state == DroneState.DOCKED:
            self.publish()
            return
        if self.fault and self.state not in (DroneState.RETURNING, DroneState.DOCKED):
            self.publish()
            return
        if self.status.failsafe and not self.fault:
            self.fail('PX4 reports failsafe; stop external control')
            self.publish()
            return
        if self.status.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD:
            self.was_offboard = True
        elif self.was_offboard and self.state not in (DroneState.RETURNING, DroneState.DOCKING, DroneState.DOCKED):
            self.fail('PX4 left Offboard; yield to its selected mode')
            self.publish()
            return
        if self.state == DroneState.TAKEOFF:
            if self.move_toward(self.home_x, self.home_y, self.home_z + self.alt) and self.was_airborne:
                self.state = DroneState.SEARCHING
                self.search_start = time.monotonic()
        elif self.state in (DroneState.RETURNING, DroneState.DOCKING):
            # PX4 RTL owns transit, descent and landing; logical docking is only
            # reported after measured landing and disarming (no tray contact claim).
            if self.was_airborne and self.land.landed and self.status.arming_state == VehicleStatus.ARMING_STATE_DISARMED:
                self.state = DroneState.DOCKED
            elif self.status.nav_state not in (VehicleStatus.NAVIGATION_STATE_AUTO_RTL, VehicleStatus.NAVIGATION_STATE_AUTO_LAND):
                self.send_command(VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
            self.publish()
            return
        else:
            previous = self.state
            self._in_behavior_tick = True
            try:
                super().tick()
            finally:
                self._in_behavior_tick = False
            if self.state == DroneState.LOITERING and previous != self.state:
                self.goal = (self.x, self.y, self.z)
        if self.state not in (DroneState.STORED, DroneState.DOCKED, DroneState.RETURNING):
            self.stream()
        self.publish()

    def publish(self):
        # One authoritative DroneState publisher for uav01, from PX4 telemetry.
        if getattr(self, '_in_behavior_tick', False) or not hasattr(self, 'received') or not self.fresh():
            return
        msg = DroneState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.header = msg.header
        msg.drone_id, msg.state = self.id, self.state
        msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z = self.x, self.y, self.z
        msg.pose.pose.orientation.z = math.sin(self.yaw / 2)
        msg.pose.pose.orientation.w = math.cos(self.yaw / 2)
        msg.battery_percent = self.battery
        msg.slot_id, msg.is_upper_position = self.slot_id, self.is_upper
        msg.standoff_distance = self.standoff
        msg.assigned_target_id = self.target.target_id if self.target else ''
        self.state_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PX4UAVAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
