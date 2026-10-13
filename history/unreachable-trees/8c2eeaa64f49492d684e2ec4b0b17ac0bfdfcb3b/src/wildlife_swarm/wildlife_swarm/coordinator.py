import copy
import math
import time

import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Target, DroneState


class Coordinator(Node):
    def __init__(self):
        super().__init__('swarm_coordinator')
        for name, value in {
                'assignment_period': 1.0, 'max_assignment_distance': 50.0,
                'distance_weight': 1.0, 'target_confidence_weight': 0.0,
                'minimum_battery_percent': 25.0, 'state_timeout_s': 3.0,
                'minimum_witnesses_for_assignment': 1}.items():
            self.declare_parameter(name, value)
        self.drones = {}
        self.last_seen = {}
        self.targets = {}
        self.assignments = {}
        self.assigned = set()
        self.assigned_targets = set()
        self.pub = self.create_publisher(Target, '/targets/assigned', 20)
        self.release_pub = self.create_publisher(Target, '/targets/released', 20)
        self.create_subscription(Target, '/targets/unassigned', self.target_cb, 20)
        self.create_subscription(Target, '/targets/registry', self.registry_cb, 20)
        self.create_subscription(DroneState, '/drones/state', self.drone_cb, 50)
        self.create_timer(float(self.get_parameter('assignment_period').value), self.report)

    def drone_cb(self, msg):
        self.drones[msg.drone_id] = msg
        self.last_seen[msg.drone_id] = time.monotonic()
        # A pause or lost telemetry does not prove the old observer has left.
        # Reassign only after a positive returning/landing state. PX4 keeps
        # responsibility for the actual return, separation and stabilization.
        if msg.state in (DroneState.RETURNING, DroneState.DOCKING, DroneState.DOCKED):
            for tid, did in list(self.assignments.items()):
                if did != msg.drone_id:
                    continue
                target = self.targets.get(tid)
                self.forget_assignment(tid)
                if target and target.status not in (Target.CLEARED, Target.LOST):
                    release = copy.deepcopy(target)
                    release.assigned_drone_id = did
                    release.status = Target.UNASSIGNED
                    self.release_pub.publish(release)
                    self.targets.pop(tid, None)
                    self.get_logger().warning(f'Releasing {tid} from returning {did}')
            self.assigned.discard(msg.drone_id)

    def forget_assignment(self, tid):
        did = self.assignments.pop(tid, None)
        self.assigned_targets.discard(tid)
        if did:
            self.assigned.discard(did)

    def registry_cb(self, target):
        self.targets[target.target_id] = copy.deepcopy(target)
        if target.status in (Target.CLEARED, Target.LOST):
            self.forget_assignment(target.target_id)

    def eligible(self, drone):
        if drone.state != DroneState.SEARCHING or drone.drone_id in self.assigned:
            return False
        age = time.monotonic() - self.last_seen.get(drone.drone_id, -math.inf)
        if age > float(self.get_parameter('state_timeout_s').value):
            return False
        battery = float(drone.battery_percent)
        return math.isfinite(battery) and (
            battery < 0 or battery >= float(self.get_parameter('minimum_battery_percent').value))

    def target_cb(self, target):
        if target.status != Target.UNASSIGNED or target.assigned_drone_id:
            return
        if target.target_id not in self.assigned_targets:
            self.targets[target.target_id] = copy.deepcopy(target)
        self.assign(target)

    def assign(self, target):
        if (target.status != Target.UNASSIGNED or target.assigned_drone_id
                or target.target_id in self.assigned_targets):
            return
        witnesses = int(self.get_parameter('minimum_witnesses_for_assignment').value)
        if witnesses > 1 and len(set(target.detecting_drones)) < witnesses:
            return
        candidates = [drone for drone in self.drones.values() if self.eligible(drone)]
        max_distance = float(self.get_parameter('max_assignment_distance').value)
        def distance(drone):
            return math.hypot(drone.pose.pose.position.x - target.pose.pose.position.x,
                              drone.pose.pose.position.y - target.pose.pose.position.y)
        candidates = [drone for drone in candidates if distance(drone) <= max_distance]
        if not candidates:
            return
        dw = float(self.get_parameter('distance_weight').value)
        cw = float(self.get_parameter('target_confidence_weight').value)
        best = min(candidates, key=lambda drone: dw * distance(drone) + cw * (1. - target.confidence))
        assigned = copy.deepcopy(target)
        assigned.assigned_drone_id = best.drone_id
        assigned.status = Target.ASSIGNED
        self.assigned.add(best.drone_id)
        self.assigned_targets.add(assigned.target_id)
        self.assignments[assigned.target_id] = best.drone_id
        self.targets[assigned.target_id] = assigned
        self.pub.publish(assigned)
        self.get_logger().info(f'Assigned {assigned.target_id} -> {best.drone_id}')

    def report(self):
        for target in list(self.targets.values()):
            self.assign(target)


def main(args=None):
    rclpy.init(args=args)
    node = Coordinator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
