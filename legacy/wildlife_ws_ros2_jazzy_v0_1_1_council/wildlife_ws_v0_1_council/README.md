# wildlife_ws — ROS 2 Jazzy v0.1.1

Council-reviewed revision of the v0.1 logic baseline. This release applies the critical architectural corrections before Gazebo integration.

## What changed
1. `wildlife_tracking` was merged into `wildlife_targets` (mux + tracker + registry).
2. String deployment triggers were replaced by typed `DeploymentRequest` messages.
3. Operator notifications use typed `OperatorAlert`; decisions use `OperatorDecision.srv`.
4. `MissionControl.srv` supports START / PAUSE / ABORT / RESET; pause/abort issue typed drone commands.
5. Tunable values are YAML parameters, loaded from launch files.
6. `setup.py` files use `find_packages()` and install parameter files cleanly.
7. RViz visualization publishes standard `MarkerArray` for UGV, UAVs, targets and standoff regions.
8. Subject 1/Subject 2 demo launch files are provided.
9. `wildlife_simulation` is now reserved for Gazebo assets/bridge configuration rather than acting as a detection-mux band-aid.

## Important scope
This is still the **logic/simulation-contract baseline**. The Gazebo world, SDF models, Nav2 integration and `ros_gz_bridge` runtime wiring are the next stage. The included bridge YAML is intentionally a placeholder and is not claimed to be operational yet.

## Build
```bash
source /opt/ros/jazzy/setup.bash
cd ~/wildlife_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Run
```bash
ros2 launch wildlife_bringup single_deployment.launch.py
ros2 launch wildlife_bringup split_deployment.launch.py
```

For Subject 1 evidence:
```bash
ros2 launch wildlife_bringup subject1_demo.launch.py
```
For Subject 2 ROS 2 architecture evidence:
```bash
ros2 launch wildlife_bringup subject2_demo.launch.py
```

Disable RViz if needed:
```bash
ros2 launch wildlife_bringup single_deployment.launch.py show_rviz:=false
```

## Operator
Keyboard in the operator-interface terminal:
```text
r uav01   -> RETURN
h uav01   -> CONTINUE HOLD
```
Or use the typed service:
```bash
ros2 service call /operator/decision wildlife_interfaces/srv/OperatorDecision \
"{target_id: 'tgt_001', assigned_drone_id: 'uav01', decision: 0, operator_notes: 'return'}"
```
Mission control:
```bash
ros2 service call /mission/control wildlife_interfaces/srv/MissionControl \
"{command: 0, operator_id: 'examiner'}"
```
`0=START 1=PAUSE 2=ABORT 3=RESET`.

## Demo sequence
- T+0: UGV starts moving.
- At deployment waypoint: typed deployment request is emitted.
- Upper/lower drones launch slot-by-slot with configured delay.
- Drones reach search altitude and run a lawnmower search.
- Dummy perception emits typed detections.
- Mux -> tracker -> registry -> swarm assignment.
- Assigned UAV moves to standoff and emits an operator alert.
- Examiner uses keyboard or ROS service for RETURN/HOLD.
- UAV returns and docks.
- RViz shows vehicle/target/standoff markers.

## Evidence checklist
### Subject 1
- UGV motion
- 8-drone deployment
- search pattern
- detection/tracking
- assignment
- standoff
- operator decision
- return/docking
- RViz visual evidence

### Subject 2
- custom msgs/srvs/actions
- nodes/topics/services
- YAML parameters
- launch composition
- state machines
- typed control path
- RViz visualization node
- package separation
