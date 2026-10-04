import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from wildlife_interfaces.msg import DroneState, UGVState, Target

STATE_NAMES = ('STORED', 'LAUNCHING', 'TAKEOFF', 'SEARCHING', 'TARGET_DETECTED',
               'STANDOFF', 'AWAITING_OPERATOR', 'RETURNING', 'DOCKING', 'DOCKED',
               'LOITERING', 'PAUSED')
TARGET_NAMES = ('UNASSIGNED', 'ASSIGNED', 'HOLD', 'AWAITING_OPERATOR', 'CLEARED', 'LOST')
PALETTE = ((.2, .7, 1.), (.3, 1., .5), (.9, .5, 1.), (1., .8, .2))


class VisualizationNode(Node):
    """Standard RViz markers for measured vehicles, observation and assignments."""
    def __init__(self):
        super().__init__('wildlife_visualization')
        for name, value in {'standoff_radius': 12.0, 'drone_marker_scale': .8,
                            'target_marker_scale': 1.0, 'state_timeout_s': 3.0,
                            'track_points': 80}.items():
            self.declare_parameter(name, value)
        self.standoff_radius = float(self.get_parameter('standoff_radius').value)
        self.drone_scale = float(self.get_parameter('drone_marker_scale').value)
        self.target_scale = float(self.get_parameter('target_marker_scale').value)
        self.drones, self.targets, self.received, self.trails = {}, {}, {}, {}
        self.ugv = None
        self.pub = self.create_publisher(MarkerArray, '/visualization/markers', 10)
        self.create_subscription(DroneState, '/drones/state', self.drone_cb, 50)
        self.create_subscription(Target, '/targets/registry', self.target_cb, 20)
        self.create_subscription(UGVState, '/ugv/state', self.ugv_cb, 20)
        self.create_timer(.2, self.publish_markers)

    def drone_cb(self, msg):
        self.drones[msg.drone_id] = msg
        self.received[msg.drone_id] = self.get_clock().now().nanoseconds
        trail = self.trails.setdefault(msg.drone_id, [])
        p = msg.pose.pose.position
        if not trail or math.dist((p.x, p.y, p.z), (trail[-1].x, trail[-1].y, trail[-1].z)) > .5:
            trail.append(Point(x=p.x, y=p.y, z=p.z))
            del trail[:-int(self.get_parameter('track_points').value)]

    def target_cb(self, msg):
        self.targets[msg.target_id] = msg

    def ugv_cb(self, msg):
        self.ugv = msg

    def marker(self, mid, namespace, kind, p, scale, color):
        msg = Marker()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.ns, msg.id, msg.type, msg.action = namespace, mid, kind, Marker.ADD
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = p
        msg.pose.orientation.w = 1.
        msg.scale.x, msg.scale.y, msg.scale.z = scale
        msg.color.r, msg.color.g, msg.color.b, msg.color.a = color
        return msg

    def publish_markers(self):
        # Rebuild our exclusive marker topic so disappearing assignments leave
        # no stale lines behind. All following markers arrive in the same array.
        arr = MarkerArray(markers=[Marker(action=Marker.DELETEALL)])
        index = 0
        now = self.get_clock().now().nanoseconds
        for did, drone in sorted(self.drones.items()):
            p = drone.pose.pose.position
            color = PALETTE[(int(did[-2:]) - 1) % len(PALETTE)]
            stale = (now - self.received[did]) * 1e-9 > float(self.get_parameter('state_timeout_s').value)
            unavailable = stale or drone.state == DroneState.PAUSED
            if unavailable:
                color = (1., .2, .2)
            arr.markers.append(self.marker(index, 'drones', Marker.CUBE,
                (p.x, p.y, p.z), (self.drone_scale,) * 3, (*color, .9)))
            index += 1
            label = self.marker(index, 'drone_labels', Marker.TEXT_VIEW_FACING,
                (p.x, p.y, p.z + 1.2), (0., 0., .65), (1., 1., 1., 1.))
            state = STATE_NAMES[drone.state] if drone.state < len(STATE_NAMES) else str(drone.state)
            battery = f'{drone.battery_percent:.0f}%' if drone.battery_percent >= 0 else '?'
            label.text = f'{did}  {state}  {battery}' + ('  STALE' if stale else '')
            arr.markers.append(label)
            index += 1
            path = self.marker(index, 'measured_paths', Marker.LINE_STRIP,
                (0., 0., 0.), (.08, 0., 0.), (*color, .65))
            path.points = self.trails.get(did, [])
            arr.markers.append(path)
            index += 1
        for tid, target in sorted(self.targets.items()):
            p = target.pose.pose.position
            faded = target.status in (Target.CLEARED, Target.LOST)
            color = (1., .45, .1, .35 if faded else .95)
            arr.markers.append(self.marker(index, 'targets', Marker.SPHERE,
                (p.x, p.y, p.z + .3), (self.target_scale,) * 3, color))
            index += 1
            label = self.marker(index, 'target_labels', Marker.TEXT_VIEW_FACING,
                (p.x, p.y, p.z + 1.6), (0., 0., .7), (1., .85, .55, 1.))
            state = TARGET_NAMES[target.status] if target.status < len(TARGET_NAMES) else str(target.status)
            label.text = f'{tid} {target.target_class} {target.confidence:.0%}\n{state} {target.assigned_drone_id}'
            arr.markers.append(label)
            index += 1
            if faded:
                continue
            radius = self.standoff_radius
            circle = self.marker(index, 'standoff', Marker.LINE_STRIP,
                (0., 0., 0.), (.10, 0., 0.), (1., .65, .1, .8))
            circle.points = [Point(x=p.x + radius * math.cos(i * math.tau / 64),
                                   y=p.y + radius * math.sin(i * math.tau / 64), z=p.z + .1) for i in range(65)]
            arr.markers.append(circle)
            index += 1
            observer = self.drones.get(target.assigned_drone_id)
            if observer:
                link = self.marker(index, 'assignments', Marker.LINE_LIST,
                    (0., 0., 0.), (.15, 0., 0.), (1., 1., .25, .9))
                q = observer.pose.pose.position
                link.points = [Point(x=p.x, y=p.y, z=p.z + .3), Point(x=q.x, y=q.y, z=q.z)]
                arr.markers.append(link)
                index += 1
        if self.ugv:
            p = self.ugv.pose.pose.position
            arr.markers.append(self.marker(index, 'ugv', Marker.CUBE,
                (p.x, p.y, p.z + .5), (2., 1.4, 1.), (.8, .8, .8, 1.)))
        self.pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = VisualizationNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
