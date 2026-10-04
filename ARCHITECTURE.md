# Wildlife ROS 2 architecture — V0.4

V0.4 preserves the confirmed V0.3 package boundaries, typed message/service/
action definitions, UAV behavior and mission FSM. One existing PX4 adapter
runs per physical SITL vehicle. No duplicate mission controller is introduced.

| Package | Responsibility |
|---|---|
| wildlife_interfaces | Frozen Detection, Target, DroneState and typed control contracts |
| wildlife_core | Shared geometry and RViz markers |
| wildlife_vehicles | Logical UGV, readiness-aware deployment, logical UAVs, docking totals |
| wildlife_perception | detector_sim, preserved logical OpenCV, real PX4-camera OpenCV and geometry |
| wildlife_targets | Detection mux, persistent tracker/fusion, lifecycle registry |
| wildlife_swarm | Health-aware observer assignment and confirmed-return reassignment |
| wildlife_mission | Existing mission FSM and typed operator decisions |
| wildlife_simulation | Worlds, cameras, moving dummy, UGV display proxy, PX4 adapter |
| wildlife_bringup | Backend selection, fleet profiles, launch and RViz configuration |

## Observation and mission flow

```text
Gazebo camera -> ros_gz_bridge -> Image + CameraInfo
PX4 attitude + measured map pose -> OpenCV camera ray/ground intersection
                                      -> Detection(map)
detector_sim --------------------------> Detection(map)
Detection -> mux -> tracker -> persistent Target registry -> coordinator
          -> assigned Target -> existing UAV behavior -> PX4 adapter
          -> namespaced PX4 command/setpoint -> PX4 -> measured DroneState
                                      |
                           OperatorAlert -> /operator/decision
```

`detector_backend` selects `sim`, `opencv` or `none`. Logic-only, PX4 synthetic,
one/two-camera and eight-PX4 lightweight profiles remain independent. YOLO
is optional and unimplemented. The legacy logical OpenCV demonstration is
preserved; the PX4 backend supplies the tested V0.4 map projection.

The local down-camera model is 640×480 at 10 Hz. Pixels use CameraInfo,
PX4 FRD/NED attitude and measured ENU map position to intersect a flat ground
plane. Ground/world Z is zero; the identity `wildlife_world -> map` transform
explicitly joins the simulation view. Geometry and temporal limitations are
in `docs/V0_4_CAMERA_GEOMETRY.md`.

Tracker IDs persist across associated observations. Class, spatial gate,
confidence/covariance and stale lifecycle rules remain distinct from observer
assignment. Finite-difference velocity summarizes track motion. Two-camera
missions use a 4 m association gate and two witnesses before assignment;
this does not guarantee separation of visually identical nearby animals.
Returning observers release their target without changing its identity.
PAUSED or stale vehicles keep their reservation until confirmed departure or
explicit recovery, preventing simultaneous observers caused by an ambiguous
fault.

## PX4 identity and health

Vehicle i uses instance i-1, MAV system ID and XRCE key i, DDS namespace
`/uavNN`, and a matching ROS adapter. Commands address the corresponding
system; ACKs are source-correlated on that namespace. Measured NED position is
converted to ENU and translated by the Gazebo spawn origin; setpoints apply
the inverse transform. Two synthetic vehicles use (0,0) and (0,-35) m;
two cameras use (0,0) and (-10,0) m with different altitude layers.
Eight vehicles use 12 m columns and separated rows, bounded +/-4 m X search
cells and no Y sweep. Altitude layers add basic mission-level separation.

The shared live PX4 profile keeps local-position freshness at two wall seconds.
Status/landing freshness inherits that limit unless explicitly overridden;
the eight-flight profile allows three seconds for these slower streams.
PX4 LandDetected publishes at one Hz of simulation time. Slower simulated
time explains long wall-clock gaps; position freshness is never extended by
the slow-stream override. Loss of mode/telemetry yields PAUSED and stops
Offboard heartbeat. ROS does not replace the PX4 native failsafe controller.
Fresh measured home landing/disarm can recover docking after a native return.
Once docking is confirmed it remains terminal across later transport loss.

Coordinator candidates must be fresh SEARCHING UAVs with adequate reported
battery. Mission logic requests one RETURN_HOME below its threshold. Unknown
battery remains configurable by the existing negative sentinel semantics;
it is not a measurement of safe energy. Live health evidence covers simulated
low battery and deliberate mode loss, rather than every PX4 failure mode.

## Deployment, completion and display

The logical UGV requests SINGLE or SPLIT deployment at existing waypoint-index
semantics. Deployment filters configured active IDs and waits for recent
readiness. LAUNCH remains queued in the PX4 adapter until ready. SPLIT flight
validated waypoint events 0/1 and exactly one launch per each of eight UAVs.
RETURN invokes native PX4 RTL. DOCKED requires measured landing/disarm at
home; the mission reaches COMPLETE only at its configured docking total.

The Gazebo UGV proxy mirrors logical pose through the set_pose service. It is
display-only and has no physical navigation or collision geometry. RViz uses
measured UAV markers/trails, IDs, state/battery/stale labels, target identity/
class/confidence, a standoff ring and assignment line. Terminal targets fade
and their active assignment graphics disappear. QGC shows native vehicle
identity/mode/arming independently; ROS remains the mission authority.

The accepted scale profile has eight PX4 vehicles and no cameras. Separate
one/two-camera missions demonstrate real-image observation and operator flow.
Evidence and remaining limitations are in `docs/V0_4_VALIDATION.md`.
