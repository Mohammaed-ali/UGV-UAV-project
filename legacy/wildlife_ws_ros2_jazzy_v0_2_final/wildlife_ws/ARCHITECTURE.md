# v0.2 architecture

```text
wildlife_interfaces
        |
        +--> wildlife_vehicles ---- UGV / deployment / UAV / docking
        |
        +--> wildlife_perception -- dummy detector / optional OpenCV detector
        |             |
        |             v
        +--> wildlife_targets ---- mux / tracker / target manager
        |             |
        |             v
        +--> wildlife_swarm ------- assignment / deconfliction
        |             |
        |             v
        +--> wildlife_mission ---- mission FSM / standoff / operator service
        |
        +--> wildlife_core -------- visualization / math / state
        |
        +--> wildlife_simulation -- Gazebo assets / ros_gz bridge / adapters
        |
        +--> wildlife_bringup ----- Subject 1 and Subject 2 launch profiles
```

### External integration boundary

`Gazebo -> ros_gz_bridge -> ROS 2`

`PX4 SITL -> ROS 2/PX4 bridge (v0.3)`

`QGroundControl -> PX4 telemetry/vehicle control (v0.3)`

`Camera -> OpenCV/YOLO -> Detection`.

The rest of the project consumes `Detection` and does not depend on the detector implementation.
