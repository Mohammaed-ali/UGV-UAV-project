"""Simulation-only live acceptance; run with the pinned ROS overlay and a local SITL."""
import argparse, json, time
parser=argparse.ArgumentParser()
parser.add_argument("--mode",choices=["target","no-target"],default="target")
parser.add_argument("--output",required=True)
args=parser.parse_args()
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Bool, String
from visualization_msgs.msg import MarkerArray
from wildlife_interfaces.msg import DroneState, OperatorAlert, Detection, Target
from wildlife_interfaces.srv import OperatorDecision
from px4_msgs.msg import VehicleStatus, VehicleLandDetected
from wildlife_simulation.px4_uav_adapter import versioned_topic

rclpy.init()
n = Node('px4_acceptance_probe')
states, stages, alerts, readiness, statuses, lands, phases = {}, {}, {}, {}, {}, {}, []
counts = {'detection':0, 'target':0, 'markers':0}
flight={'gcs_connected':False,'offboard':False,'armed':False,'max_z':0.,'positions':[], 'publisher_count':0}
def status(m):
    statuses['uav01']=m
    flight['gcs_connected'] |= not m.gcs_connection_lost
    flight['offboard'] |= m.nav_state==VehicleStatus.NAVIGATION_STATE_OFFBOARD
    flight['armed'] |= m.arming_state==VehicleStatus.ARMING_STATE_ARMED
def state(m):
    states[m.drone_id] = m
    stages.setdefault(m.drone_id,set()).add(m.state)
    p=m.pose.pose.position
    flight['max_z']=max(flight['max_z'],p.z)
    flight['positions'].append((p.x,p.y))
def phase(m):
    if not phases or phases[-1] != m.data.split('Phase=')[1].split()[0]:
        phases.append(m.data.split('Phase=')[1].split()[0])
def count(key):
    return lambda m: counts.update({key:counts[key]+1})
n.create_subscription(DroneState,'/drones/state',state,50)
n.create_subscription(OperatorAlert,'/operator/alerts',lambda m:alerts.update({m.drone_id:m}),20)
n.create_subscription(String,'/mission/status',phase,10)
n.create_subscription(Detection,'/detections/all',count('detection'),20)
n.create_subscription(Target,'/targets/assigned',count('target'),20)
n.create_subscription(MarkerArray,'/visualization/markers',count('markers'),10)
n.create_subscription(Bool,'/drones/uav01/ready',lambda m:readiness.update({'seen_true':readiness.get('seen_true',False) or m.data}),10)
n.create_subscription(VehicleStatus,versioned_topic('/uav01','out','vehicle_status',VehicleStatus),status,qos_profile_sensor_data)
n.create_subscription(VehicleLandDetected,versioned_topic('/uav01','out','vehicle_land_detected',VehicleLandDetected),lambda m:lands.update({'uav01':m}),qos_profile_sensor_data)
client=n.create_client(OperatorDecision,'/operator/decision')
held,returned=set(),set()
hold_time={}
pending=None
start=time.monotonic()
while time.monotonic()-start < 225:
    rclpy.spin_once(n,timeout_sec=.1)
    if pending:
        if not pending.done(): continue
        res=pending.result()
        if not res.accepted: raise RuntimeError(res.message)
        pending=None
    for did,alert in list(alerts.items()):
        if did in returned or did not in states or states[did].state!=DroneState.AWAITING_OPERATOR: continue
        if did in held and time.monotonic()-hold_time[did]<3: continue
        decision=OperatorDecision.Request.RETURN if did in held else OperatorDecision.Request.CONTINUE_HOLD
        pending=client.call_async(OperatorDecision.Request(target_id=alert.target_id,assigned_drone_id=did,decision=decision,operator_notes='Simulation acceptance probe'))
        if did in held: returned.add(did)
        else: held.add(did);hold_time[did]=time.monotonic()
        break
    if states and states['uav01'].state==DroneState.DOCKED and phases and phases[-1]=='COMPLETE': break
    if int(time.monotonic()-start)%15==0 and time.monotonic()-getattr(n,'printed',-100)>1:
        print('progress',len(states),{k:v.state for k,v in states.items()},readiness,phases[-1:] ,flush=True);n.printed=time.monotonic()
flight['publisher_count']=len(n.get_publishers_info_by_topic('/drones/state'))
positions=flight.pop('positions')
flight['horizontal_span_m']=max((max(x for x,y in positions)-min(x for x,y in positions),max(y for x,y in positions)-min(y for x,y in positions)),default=0.) if positions else 0.
result={'mode':args.mode,'flight':flight,'elapsed_s':round(time.monotonic()-start,1),'states':{k:v.state for k,v in states.items()},'stages':{k:sorted(v) for k,v in stages.items()},'held':sorted(held),'returned':sorted(returned),'ready':readiness,'phases':phases,'counts':counts,'px4_landed':bool(lands and lands['uav01'].landed),'px4_disarmed':bool(statuses and statuses['uav01'].arming_state==VehicleStatus.ARMING_STATE_DISARMED)}
passed=(set(states)=={'uav01'} and states['uav01'].state==DroneState.DOCKED and result['px4_landed'] and result['px4_disarmed'] and phases[-1:] == ['COMPLETE'] and counts['markers'] and flight['offboard'] and flight['armed'] and flight['gcs_connected'] and flight['publisher_count']==1 and readiness.get('seen_true') and DroneState.SEARCHING in stages['uav01'])
if args.mode=='target': passed=passed and held and returned and counts['target'] and counts['detection'] and DroneState.STANDOFF in stages['uav01']
else: passed=passed and not held and not counts['target'] and DroneState.LOITERING in stages['uav01']
result['result']='PASS' if passed else 'FAIL'
open(args.output,'w').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
n.destroy_node();rclpy.shutdown()
raise SystemExit(0 if passed else 1)
