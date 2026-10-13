"""Single-SITL boundary tests; require the pinned px4_msgs overlay."""
import math
import time
import unittest
from unittest.mock import patch
import rclpy
from px4_msgs.msg import VehicleLocalPosition, VehicleStatus, VehicleLandDetected, VehicleCommand, VehicleCommandAck
from wildlife_interfaces.msg import DroneCommand, DroneState
from wildlife_simulation.px4_uav_adapter import PX4UAVAdapter, enu_to_ned, ned_to_enu, versioned_topic

class Capture:
    def __init__(self): self.messages=[]
    def publish(self,msg): self.messages.append(msg)

class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): rclpy.init(args=['--ros-args','-p','sitl_enabled:=true'])
    @classmethod
    def tearDownClass(cls): rclpy.shutdown()
    def setUp(self):
        self.n=PX4UAVAdapter()
        for attr in ('command_pub','heartbeat_pub','setpoint_pub','state_pub'):
            setattr(self.n,attr,Capture())
        self.n.status_cb(VehicleStatus(pre_flight_checks_pass=True, arming_state=VehicleStatus.ARMING_STATE_DISARMED))
        self.n.land_cb(VehicleLandDetected(landed=True))
        self.n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True,x=2.,y=3.,z=-4.,heading=0.))
    def tearDown(self): self.n.destroy_node()
    def test_frame_conversion_and_versioned_topics(self):
        self.assertEqual(enu_to_ned((1,2,3)),[2.,1.,-3.])
        self.assertEqual(ned_to_enu(enu_to_ned((1,2,3))),(1.,2.,3.))
        self.assertEqual(versioned_topic('', 'out', 'vehicle_status',VehicleStatus),'/fmu/out/vehicle_status_v1')
    def test_telemetry_is_only_position_authority(self):
        n=self.n
        n.move_toward(5.,6.,10.)
        self.assertEqual((n.x,n.y,n.z),(3.,2.,4.))
        n.publish()
        p=n.state_pub.messages[-1].pose.pose.position
        self.assertEqual((p.x,p.y,p.z),(3.,2.,4.))
        self.assertEqual(n.state_pub.messages[-1].header.frame_id,'map')
    def test_invalid_position_rejects_commands(self):
        n=self.n
        n.local_cb(VehicleLocalPosition(xy_valid=False,z_valid=True))
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        self.assertEqual(n.state,DroneState.STORED)
        n.tick()
        self.assertFalse(n.heartbeat_pub.messages)
    def test_prestream_before_offboard_or_arm(self):
        n=self.n
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        n.tick()
        self.assertEqual(n.state,DroneState.TAKEOFF)
        self.assertTrue(n.heartbeat_pub.messages)
        self.assertFalse(n.command_pub.messages)
        n.stream_start=time.monotonic()-2
        n.tick()
        self.assertEqual(n.command_pub.messages[-1].command,VehicleCommand.VEHICLE_CMD_DO_SET_MODE)
    def test_stale_telemetry_stops_heartbeat(self):
        n=self.n
        n.stream_start=time.monotonic()-2
        n.received['local']=time.monotonic()-10
        n.tick()
        self.assertIsNotNone(n.fault)
        self.assertFalse(n.heartbeat_pub.messages)
    def test_origin_reset_faults_after_takeoff(self):
        n=self.n;n.was_airborne=True
        n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True,xy_reset_counter=1))
        self.assertIsNotNone(n.fault)
    def test_rejected_command_and_bounds_fault(self):
        n=self.n
        n.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE,1.,6.)
        n.ack_cb(VehicleCommandAck(command=VehicleCommand.VEHICLE_CMD_DO_SET_MODE,result=VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED,target_system=255,target_component=1))
        self.assertIsNotNone(n.fault)
        self.assertFalse(n.move_toward(1000.,0.,10.))
    def test_return_uses_px4_rtl_and_measured_landing(self):
        n=self.n;n.state=DroneState.RETURNING;n.was_airborne=True
        n.land_cb(VehicleLandDetected(landed=False))
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_ARMED))
        n.tick()
        self.assertEqual(n.command_pub.messages[-1].command,VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
        self.assertNotEqual(n.state,DroneState.DOCKED)
        n.land_cb(VehicleLandDetected(landed=True))
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_DISARMED))
        n.tick()
        self.assertEqual(n.state,DroneState.DOCKED)

    def test_launch_is_queued_until_telemetry_recovers(self):
        n=self.n
        n.received.clear()
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        self.assertTrue(n.pending_launch)
        n.tick()
        self.assertEqual(n.state,DroneState.STORED)
        n.status_cb(VehicleStatus(pre_flight_checks_pass=True))
        n.land_cb(VehicleLandDetected(landed=True))
        n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True))
        n.tick()
        self.assertFalse(n.pending_launch)
        self.assertEqual(n.state,DroneState.TAKEOFF)
    def test_abort_before_readiness_cancels_launch(self):
        n=self.n;n.received.clear()
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.RETURN_HOME))
        self.assertFalse(n.pending_launch)
        self.assertTrue(n.launch_inhibited)
        n.tick()
        self.assertFalse(n.command_pub.messages)
    def test_pause_before_readiness_latches_until_resume(self):
        n=self.n;n.received.clear()
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.HOLD_POSITION))
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        self.assertFalse(n.pending_launch)
        self.assertTrue(n.launch_inhibited)
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.RESUME))
        self.assertFalse(n.launch_inhibited)
    def test_spawn_origin_applies_in_both_directions(self):
        n=self.n;n.origin=(10.,20.,1.)
        n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True,x=2.,y=3.,z=-4.))
        self.assertEqual((n.x,n.y,n.z),(13.,22.,5.))
        n.goal=(13.,22.,15.)
        n.stream()
        self.assertEqual(list(n.setpoint_pub.messages[-1].position),[2.,3.,-14.])
    def test_search_lanes_stay_bounded(self):
        n=self.n;n.home_z=0.
        n.half_width=3.;n.lane=5.
        visited=[]
        for _ in range(25):
            n.lawnmower_step()
            visited.append(n.search_goal)
            n.x,n.y,n.z=n.search_goal
        self.assertLessEqual(max(y for _,y,_ in visited),30.)
        self.assertGreater(len(set(visited)),2)

    def test_other_command_sources_do_not_fault_adapter(self):
        n=self.n
        n.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE)
        n.ack_cb(VehicleCommandAck(command=VehicleCommand.VEHICLE_CMD_DO_SET_MODE,result=VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED,target_system=254,target_component=190))
        self.assertIsNone(n.fault)
    def test_fault_cannot_resume_when_telemetry_is_stale(self):
        n=self.n;n.fail('test fault');n.received.clear()
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.RESUME))
        self.assertEqual(n.state,DroneState.PAUSED)
        self.assertFalse(n.heartbeat_pub.messages)
    def test_fresh_fault_publishes_paused_and_explicit_return_can_dock(self):
        n=self.n;n.was_airborne=True;n.fail('test fault')
        n.tick()
        self.assertEqual(n.state_pub.messages[-1].state,DroneState.PAUSED)
        self.assertFalse(n.heartbeat_pub.messages)
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.RETURN_HOME))
        n.tick()
        self.assertEqual(n.state,DroneState.DOCKED)
        self.assertFalse(n.heartbeat_pub.messages)

    def test_confirmed_docking_survives_later_telemetry_loss(self):
        n=self.n; n.state=DroneState.DOCKED; n.was_airborne=True
        n.stream_start=time.monotonic()-2; n.received.clear()
        n.tick()
        self.assertEqual(n.state,DroneState.DOCKED)
        self.assertIsNone(n.fault)

    def test_faulted_native_landing_needs_fresh_home_landing_and_disarm(self):
        n=self.n; n.was_airborne=True; n.fail('native recovery')
        n.home_x,n.home_y=n.x,n.y
        n.land_cb(VehicleLandDetected(landed=False))
        n.tick(); self.assertEqual(n.state,DroneState.PAUSED)
        n.land_cb(VehicleLandDetected(landed=True))
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_ARMED))
        n.tick(); self.assertEqual(n.state,DroneState.PAUSED)
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_DISARMED))
        n.home_x+=10.
        n.tick(); self.assertEqual(n.state,DroneState.PAUSED)
        n.home_x=n.x
        n.tick(); self.assertEqual(n.state,DroneState.DOCKED)
        self.assertFalse(n.heartbeat_pub.messages)

    def test_slow_status_timeout_never_extends_position_timeout(self):
        from rclpy.parameter import Parameter
        n=self.n
        n.set_parameters([Parameter('status_land_timeout_s', value=3.0)])
        now=time.monotonic()
        n.received['land']=now-1.5; n.received['status']=now-1.5
        self.assertTrue(n.fresh())
        n.received['local']=now-1.5
        self.assertFalse(n.fresh())
        n.received['local']=now; n.received['land']=now-4.
        self.assertFalse(n.fresh())

if __name__=='__main__':unittest.main()
