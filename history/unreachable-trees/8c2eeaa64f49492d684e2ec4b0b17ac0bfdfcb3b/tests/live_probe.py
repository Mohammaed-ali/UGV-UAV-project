"""Logic-only acceptance: eight deployments, operator decisions and completion."""
import argparse
import json
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from wildlife_interfaces.msg import DroneState, DroneCommand, DeploymentRequest, OperatorAlert
from wildlife_interfaces.srv import OperatorDecision
from visualization_msgs.msg import MarkerArray

parser = argparse.ArgumentParser()
parser.add_argument('--output')
args = parser.parse_args()
rclpy.init()
n = Node('wildlife_validation_probe')
states, alerts, markers, phases, launches, events = {}, {}, [], [], [], []
n.create_subscription(DroneState, '/drones/state', lambda m: states.update({m.drone_id: m.state}), 50)
n.create_subscription(OperatorAlert, '/operator/alerts', lambda m: alerts.update({m.drone_id: m}), 20)
n.create_subscription(MarkerArray, '/visualization/markers', lambda m: markers.append(len(m.markers)), 10)
qos = QoSProfile(depth=32, durability=DurabilityPolicy.TRANSIENT_LOCAL)
n.create_subscription(DroneCommand, '/deployment/commands',
                      lambda m: launches.append(m.drone_id) if m.command == DroneCommand.LAUNCH else None, qos)
n.create_subscription(DeploymentRequest, '/ugv/deployment_request',
                      lambda m: events.append({'mode': m.deployment_mode, 'waypoint': m.waypoint_index}), qos)


def phase_cb(msg):
    if 'Phase=' in msg.data:
        phase = msg.data.split('Phase=')[1].split()[0]
        if not phases or phases[-1] != phase:
            phases.append(phase)


n.create_subscription(String, '/mission/status', phase_cb, 10)
client = n.create_client(OperatorDecision, '/operator/decision')
start = time.monotonic()
held, returned = set(), set()
pending = None
result = {'result': 'FAIL', 'failure': ''}
try:
    while time.monotonic() - start < 250:
        rclpy.spin_once(n, timeout_sec=.1)
        if pending:
            if not pending.done():
                continue
            response = pending.result()
            assert response.accepted, response.message
            pending = None
        for did, alert in list(alerts.items()):
            if states.get(did) != DroneState.AWAITING_OPERATOR or did in returned:
                continue
            decision = OperatorDecision.Request.CONTINUE_HOLD if did not in held else OperatorDecision.Request.RETURN
            pending = client.call_async(OperatorDecision.Request(
                target_id=alert.target_id, assigned_drone_id=did, decision=decision))
            (held if decision == OperatorDecision.Request.CONTINUE_HOLD else returned).add(did)
            break
        if 'COMPLETE' in phases and len(states) == 8 and all(s == DroneState.DOCKED for s in states.values()):
            break
    assert len(states) == 8 and all(s == DroneState.DOCKED for s in states.values()), states
    assert markers and held and returned and 'COMPLETE' in phases
    assert launches == [f'uav{i:02d}' for i in range(1, 9)], launches
    assert {'mode': 'SINGLE', 'waypoint': 0} in events, events
    result['result'] = 'PASS'
except Exception as exc:
    result['failure'] = str(exc) or type(exc).__name__
finally:
    result.update(elapsed_s=round(time.monotonic() - start, 1), states=states,
                  held=sorted(held), returned=sorted(returned), phases=phases,
                  launches=launches, deployment_events=events,
                  marker_messages=len(markers), max_markers=max(markers, default=0))
    report = json.dumps(result, indent=2)
    print(report, flush=True)
    if args.output:
        Path(args.output).write_text(report + '\n')
    n.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
