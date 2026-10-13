"""Behavioral regression checks using installed ROS types and actual node classes.

Run after sourcing Jazzy and install/setup.bash:
  python3 -m unittest discover -s tests -v
"""
import copy
import math
import time
import unittest
from unittest.mock import patch

import rclpy
from rclpy.parameter import Parameter
from wildlife_interfaces.msg import Detection, DroneCommand, DroneState, Target, OperatorAlert, DeploymentRequest, UGVState
from wildlife_interfaces.srv import OperatorDecision, MissionControl
from wildlife_vehicles.uav_node import UAVNode
from wildlife_vehicles.ugv_node import UGVNode
from wildlife_vehicles.deployment_node import DeploymentNode
from wildlife_targets.tracker import Tracker
from wildlife_targets.target_manager import TargetManager
from wildlife_swarm.coordinator import Coordinator
from wildlife_mission.operator_interface import OperatorInterface
from wildlife_mission.mission_manager import MissionManager, Phase
from wildlife_perception.detector_sim import DetectorSim
from wildlife_simulation.ugv_gazebo_adapter import heading_command, UGVGazeboAdapter


class Capture:
    def __init__(self):
        self.messages = []
    def publish(self, message):
        self.messages.append(copy.deepcopy(message))


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init(args=['--ros-args', '-p', 'input_enabled:=false'])
    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()
    def setUp(self):
        self.nodes = []
    def tearDown(self):
        for node in reversed(self.nodes):
            node.destroy_node()
    def node(self, cls):
        node = cls()
        self.nodes.append(node)
        return node
    def detection(self, x=1., cls='dummy_animal'):
        d = Detection(drone_id='uav01', target_class=cls, confidence=0.9)
        d.position_world.x = x
        return d
    def test_tracker_association_expiry_and_monotonic_ids(self):
        n = self.node(Tracker)
        n.pub = Capture()
        n.cb(self.detection())
        n.cb(self.detection(1.2))
        self.assertEqual(len(n.tracks), 1)
        self.assertEqual(n.tracks['tgt_001'].count, 2)
        n.cb(self.detection(1.2, 'different_class'))
        n.cb(self.detection(20.))
        self.assertEqual(len(n.tracks), 3)
        with patch('wildlife_targets.tracker.time.monotonic', return_value=time.monotonic()+30):
            n.expire()
        self.assertFalse(n.tracks)
        self.assertEqual(n.pub.messages[-1].status, Target.LOST)
        n.cb(self.detection())
        self.assertIn('tgt_004', n.tracks)
    def test_two_source_fusion_and_moving_target_velocity(self):
        n = self.node(Tracker)
        n.pub = Capture()
        for index, did in enumerate(('uav01', 'uav02', 'uav01', 'uav02')):
            detection = self.detection(x=float(index))
            detection.drone_id = did
            detection.header.stamp.sec = 100 + index
            detection.covariance_xx = detection.covariance_yy = 4.
            n.cb(detection)
        self.assertEqual(len(n.tracks), 1)
        fused = n.pub.messages[-1]
        self.assertEqual(fused.target_id, 'tgt_001')
        self.assertEqual(set(fused.detecting_drones), {'uav01', 'uav02'})
        self.assertEqual(fused.detection_count, 4)
        self.assertGreater(fused.velocity_estimate.linear.x, .2)
        self.assertLess(fused.fused_covariance_xx, 4.)
        different = self.detection(x=20.)
        different.header.stamp.sec = 104
        n.cb(different)
        self.assertEqual(len(n.tracks), 2)
    def test_target_lifecycle_survives_measurement(self):
        n = self.node(TargetManager)
        n.tracked_cb(Target(target_id='t1'))
        n.assigned_cb(Target(target_id='t1', assigned_drone_id='uav02'))
        n.decision_cb(Target(target_id='t1', status=Target.STANDOFF_HOLD))
        n.tracked_cb(Target(target_id='t1', confidence=0.95))
        self.assertEqual(n.db['t1'].assigned_drone_id, 'uav02')
        self.assertEqual(n.db['t1'].status, Target.STANDOFF_HOLD)
        self.assertTrue(n.db['t1'].operator_notified)
    def test_assignment_reserves_target_before_registry_feedback(self):
        n = self.node(Coordinator)
        n.pub = Capture()
        for did in ('uav01', 'uav02'):
            n.drone_cb(DroneState(drone_id=did, state=DroneState.SEARCHING, battery_percent=100.))
        n.target_cb(Target(target_id='t1'))
        n.target_cb(Target(target_id='t1'))
        self.assertEqual(len(n.pub.messages), 1)
    def test_assignment_excludes_low_battery_and_stale_vehicle(self):
        n = self.node(Coordinator)
        n.pub = Capture()
        n.drone_cb(DroneState(drone_id='uav01', state=DroneState.SEARCHING, battery_percent=10.))
        n.drone_cb(DroneState(drone_id='uav02', state=DroneState.SEARCHING, battery_percent=80.))
        n.target_cb(Target(target_id='t1'))
        self.assertEqual(n.pub.messages[-1].assigned_drone_id, 'uav02')
        n.assigned.clear()
        n.last_seen['uav02'] -= 10.
        n.target_cb(Target(target_id='t2'))
        self.assertEqual(len(n.pub.messages), 1)
        n.drone_cb(DroneState(drone_id='uav02', state=DroneState.RETURNING, battery_percent=80.))
        n.target_cb(Target(target_id='t2'))
        self.assertEqual(len(n.pub.messages), 1)
    def test_single_and_split_deployment_deduplicate(self):
        for mode in ('SINGLE', 'SPLIT'):
            n = self.node(DeploymentNode)
            n.delay = 0.
            n.cmd_pub = Capture()
            for wp in (0, 0, 1, 1):
                n.request_cb(DeploymentRequest(deployment_mode=mode, waypoint_index=wp))
            self.assertEqual(len(n.pending), 8)
            for _ in range(20):
                n.tick()
            self.assertEqual(len(n.cmd_pub.messages), 8)
            self.assertEqual(len({m.drone_id for m in n.cmd_pub.messages}), 8)
    def test_px4_deployment_requires_recent_ready_and_filters_active_ids(self):
        n=self.node(DeploymentNode)
        n.active_ids={'uav01'};n.require_ready=True;n.delay=0.;n.cmd_pub=Capture()
        n.request_cb(DeploymentRequest(deployment_mode='SINGLE'))
        self.assertEqual([item[0] for item in n.pending],['uav01'])
        n.tick()
        self.assertFalse(n.cmd_pub.messages)
        n.readiness['uav01']=(True,time.monotonic()-2)
        n.tick()
        self.assertFalse(n.cmd_pub.messages)
        n.readiness['uav01']=(True,time.monotonic())
        n.tick()
        self.assertEqual([m.drone_id for m in n.cmd_pub.messages],['uav01'])

    def test_deployment_pause_resume_abort(self):
        n = self.node(DeploymentNode)
        n.delay = 0.
        n.cmd_pub = Capture()
        n.request_cb(DeploymentRequest(deployment_mode='SINGLE'))
        n.control_cb(DroneCommand(drone_id='uav01', command=DroneCommand.HOLD_POSITION))
        n.tick()
        self.assertFalse(n.cmd_pub.messages)
        n.control_cb(DroneCommand(drone_id='uav01', command=DroneCommand.RESUME))
        n.tick()
        self.assertEqual(n.cmd_pub.messages[0].drone_id, 'uav01')
        for i in range(2, 9):
            n.control_cb(DroneCommand(drone_id=f'uav{i:02d}', command=DroneCommand.RETURN_HOME))
        n.request_cb(DeploymentRequest(deployment_mode='SINGLE'))
        self.assertFalse(n.pending)
    def test_late_deployment_subscriber_receives_waypoint_zero(self):
        ugv = self.node(UGVNode)
        ugv.tick()  # Publish before the deployment subscriber exists.
        deployment = self.node(DeploymentNode)
        # Prevent timers from consuming the observed queue during this check.
        for timer in deployment.timers:
            timer.cancel()
        deadline = time.monotonic() + 5
        while not deployment.pending and time.monotonic() < deadline:
            rclpy.spin_once(deployment, timeout_sec=.1)
        self.assertEqual(len(deployment.pending), 8)

    def test_mission_recovers_from_missed_ugv_deploying_edge(self):
        n = self.node(MissionManager)
        n.drone_cb(DroneState(drone_id='uav01', state=DroneState.SEARCHING))
        self.assertEqual(n.phase, Phase.SEARCHING)
    def test_mission_requests_one_low_battery_return(self):
        n = self.node(MissionManager)
        n.cmd_pub = Capture()
        low = DroneState(drone_id='uav01', state=DroneState.SEARCHING, battery_percent=15.)
        n.drone_cb(low)
        n.drone_cb(low)
        self.assertEqual([(m.drone_id, m.command) for m in n.cmd_pub.messages],
                         [('uav01', DroneCommand.RETURN_HOME)])

    def test_ugv_waypoint_index_and_split(self):
        n = self.node(UGVNode)
        n.mode = 'SPLIT'
        n.deploy_at = {0, 1}
        n.speed = 200.
        n.state_pub = Capture()
        n.deploy_pub = Capture()
        for _ in range(30):
            n.tick()
        self.assertEqual([m.waypoint_index for m in n.deploy_pub.messages], [0, 1])
        self.assertEqual(n.state_pub.messages[-1].current_waypoint_index, 2)
        self.assertEqual(n.state_pub.messages[-1].state, UGVState.MISSION_COMPLETE)
    def test_hold_then_return_and_invalid_decision(self):
        operator = self.node(OperatorInterface)
        operator.pub = Capture()
        uav = self.node(UAVNode)
        uav.target = Target(target_id='t1', assigned_drone_id=uav.id)
        uav.state = DroneState.AWAITING_OPERATOR
        operator.alert_cb(OperatorAlert(drone_id=uav.id, target_id='t1', severity=OperatorAlert.ACTION_REQUIRED))
        self.assertFalse(operator.apply(uav.id, 99))
        self.assertTrue(operator.apply(uav.id, OperatorDecision.Request.CONTINUE_HOLD))
        uav.decision_cb(operator.pub.messages[-1])
        self.assertEqual(uav.state, DroneState.AWAITING_OPERATOR)
        self.assertTrue(operator.apply(uav.id, OperatorDecision.Request.RETURN))
        uav.decision_cb(operator.pub.messages[-1])
        self.assertEqual(uav.state, DroneState.RETURNING)
        self.assertFalse(operator.pending)
    def test_launch_search_standoff_return_dock(self):
        n = self.node(UAVNode)
        n.speed = 100.
        n.command_cb(DroneCommand(drone_id=n.id, command=DroneCommand.LAUNCH))
        n.tick(); n.tick()
        self.assertEqual(n.state, DroneState.SEARCHING)
        n.target_cb(Target(target_id='t1', assigned_drone_id=n.id))
        for _ in range(10): n.tick()
        self.assertEqual(n.state, DroneState.AWAITING_OPERATOR)
        n.decision_cb(Target(target_id='t1', assigned_drone_id=n.id, status=Target.CLEARED))
        for _ in range(10): n.tick()
        self.assertEqual(n.state, DroneState.DOCKED)
    def test_pause_restores_takeoff_return_and_operator_wait(self):
        n = self.node(UAVNode)
        for state in (DroneState.TAKEOFF, DroneState.RETURNING, DroneState.AWAITING_OPERATOR):
            n.state = state
            n.command_cb(DroneCommand(drone_id=n.id, command=DroneCommand.HOLD_POSITION))
            n.command_cb(DroneCommand(drone_id=n.id, command=DroneCommand.HOLD_POSITION))
            n.tick()
            self.assertEqual(n.state, DroneState.PAUSED)
            n.command_cb(DroneCommand(drone_id=n.id, command=DroneCommand.RESUME))
            self.assertEqual(n.state, state)
    def test_mission_completes_and_override_not_lost_to_alert(self):
        n = self.node(MissionManager)
        n.phase = Phase.RESOLVING
        for i in range(1, 9):
            n.drone_cb(DroneState(drone_id=f'uav{i:02d}', state=DroneState.DOCKED))
        self.assertEqual(n.phase, Phase.COMPLETE)
        for phase in (Phase.PAUSED, Phase.ABORTED, Phase.COMPLETE):
            n.phase = phase
            n.alert_cb(OperatorAlert(severity=OperatorAlert.ACTION_REQUIRED))
            self.assertEqual(n.phase, phase)
        res = n.control_cb(MissionControl.Request(command=MissionControl.Request.RESET), MissionControl.Response())
        self.assertFalse(res.accepted)
    def test_seeded_detector_repeats_measurements_and_ids(self):
        a, b = self.node(DetectorSim), self.node(DetectorSim)
        for n in (a, b):
            n.pub = Capture()
            n.state = DroneState.SEARCHING
            n.x, n.y = 15., 12.
            for _ in range(20): n.tick()
        def values(n):
            return [(d.detection_id, d.confidence, d.position_world.x, d.position_world.y) for d in n.pub.messages]
        self.assertTrue(a.pub.messages)
        self.assertEqual(values(a), values(b))
    def test_heading_uses_current_yaw_and_shortest_turn(self):
        linear, angular = heading_command(0, 0, math.pi/2, 0, 10, 1.2, 1.8, 1.5, .5)
        self.assertAlmostEqual(angular, 0)
        self.assertGreater(linear, 0)
        linear, angular = heading_command(0, 0, math.pi, 10, 0, 1.2, 1.8, 1.5, .5)
        self.assertEqual(linear, 0)
        self.assertLessEqual(abs(angular), 1.5)
    def test_adapter_stops_without_telemetry(self):
        n = self.node(UGVGazeboAdapter)
        n.pub = Capture()
        n.cb(UGVState(state=UGVState.MOVING))
        n.tick()
        self.assertEqual(n.pub.messages[-1].linear.x, 0)
        self.assertEqual(n.pub.messages[-1].angular.z, 0)


if __name__ == '__main__':
    unittest.main()
