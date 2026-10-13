# Wildlife ROS 2 architecture — v0.1.1 council revision

The v0.1 architecture is retained. The council changes are targeted integration fixes, not another redesign.

## Packages
- `wildlife_interfaces`: typed msgs/srvs/actions.
- `wildlife_core`: shared visualization/common utilities.
- `wildlife_perception`: replaceable detector simulation.
- `wildlife_targets`: detection mux + tracking + target lifecycle (tracking merged here).
- `wildlife_swarm`: assignment/deconfliction.
- `wildlife_mission`: mission FSM + operator decision service.
- `wildlife_vehicles`: UGV/UAV/deployment/docking.
- `wildlife_simulation`: reserved simulation assets/bridge configuration for Gazebo stage.
- `wildlife_bringup`: launch, YAML composition and RViz demo.

## Critical data flow
UGV -> typed DeploymentRequest -> Deployment Manager -> typed DroneCommand -> UAVs
UAVs -> Detection -> wildlife_targets mux -> tracker -> target registry -> swarm assignment -> UAV standoff -> OperatorAlert -> OperatorDecision -> return/hold
State visualization -> MarkerArray -> RViz2

## Design decisions from council review
- Tracking is merged into `wildlife_targets` to remove one package/topic hop.
- Operational control uses typed ROS interfaces; String is retained only for human-readable status output.
- Tunable values are in YAML and loaded by launch files.
- RViz is a first-class demo surface.
- Subject 1 and Subject 2 launch entry points are explicit.
- Gazebo/ros_gz bridge configuration is reserved for the next stage; this release does not pretend the bridge is complete.
