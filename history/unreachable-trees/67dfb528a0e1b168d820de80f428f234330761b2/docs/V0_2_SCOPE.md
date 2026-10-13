# Wildlife ROS 2 v0.2 scope

v0.2 implements the council changes from v0.1.1 and adds the first Gazebo layer.

### Included
1. `wildlife_tracking` is merged into `wildlife_targets`.
2. Typed deployment/operator/mission interfaces are used instead of String command parsing.
3. YAML parameter files are installed with the packages.
4. RViz visualization and dedicated Subject 1 / Subject 2 demo launches are retained.
5. Gazebo world + UGV + 8 UAV visual proxy models are included.
6. `ros_gz_sim` spawning and a minimal `ros_gz_bridge` configuration are included.
7. OpenCV camera detection plumbing is available as an optional backend.
8. The existing dummy detector remains available for deterministic demonstrations.
9. PX4 SITL/QGroundControl/micro-ROS/YOLO are documented as later integration layers.

### Not claimed as complete in v0.2
- PX4 flight dynamics or PX4 offboard control.
- QGroundControl mission control integration.
- YOLO inference.
- Nav2 autonomous UGV navigation.
- Full Gazebo-to-ROS synchronization for every UAV state.

These are intentionally staged for v0.3 rather than making v0.2 depend on a large external stack.

## V0.2 final review notes

- The UAVs in Gazebo remain static visual proxies. Their authoritative simulated flight state is still the ROS 2 UAV state machine; PX4-driven physical flight is a V0.3 integration.
- Each UAV proxy now has a Gazebo camera sensor and a unique ROS image topic. The optional OpenCV detector can consume these images through `cv_bridge`.
- The default V0.2 demonstration continues to use the deterministic detector simulator so the core mission demo remains reproducible.
- `simulation.launch.py` now loads the vehicle and perception YAML files for the corresponding nodes; UAV timing/search parameters are therefore not silently replaced by Python defaults.
- `UGVState.current_waypoint_index` is explicitly defined as the last completed waypoint; the Gazebo adapter commands the following waypoint.

