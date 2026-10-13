"""Simulation-only probe; validates operator HOLD then RETURN and MarkerArray."""
import json
import time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import DroneState, OperatorAlert
from wildlife_interfaces.srv import OperatorDecision
from visualization_msgs.msg import MarkerArray
rclpy.init()
n = Node('wildlife_validation_probe')
states, alerts, markers = {}, {}, []
n.create_subscription(DroneState, '/drones/state', lambda m: states.update({m.drone_id: m.state}), 50)
n.create_subscription(OperatorAlert, '/operator/alerts', lambda m: alerts.update({m.drone_id: m}), 20)
n.create_subscription(MarkerArray, '/visualization/markers', lambda m: markers.append(len(m.markers)), 10)
client = n.create_client(OperatorDecision, '/operator/decision')
deadline = time.monotonic() + 250
held, returned = set(), set()
pending = None
while time.monotonic() < deadline:
    rclpy.spin_once(n, timeout_sec=.1)
    if pending:
        if not pending.done(): continue
        result = pending.result()
        assert result.accepted, result.message
        pending = None
    for did, alert in list(alerts.items()):
        if states.get(did) != DroneState.AWAITING_OPERATOR or did in returned: continue
        decision = OperatorDecision.Request.CONTINUE_HOLD if did not in held else OperatorDecision.Request.RETURN
        pending = client.call_async(OperatorDecision.Request(target_id=alert.target_id, assigned_drone_id=did, decision=decision))
        (held if decision == OperatorDecision.Request.CONTINUE_HOLD else returned).add(did)
        break
    if len(states) == 8 and all(s == DroneState.DOCKED for s in states.values()): break
result = {'states': states, 'held': sorted(held), 'returned': sorted(returned), 'marker_messages': len(markers), 'max_markers': max(markers, default=0)}
print(json.dumps(result, indent=2), flush=True)
n.destroy_node(); rclpy.shutdown()
assert len(states) == 8 and markers and held and returned and all(s == DroneState.DOCKED for s in states.values()), result
