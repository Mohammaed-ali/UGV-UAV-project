# V0.4 build report — 2026-10-04

V0.4 is the validated academic continuation of `v0.3-final` (`8ca1e9d`) in
`/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`, branch
`codex/v0.4-development`. The applicable release gates passed for the
configured demonstrations described below. Release identity: **`v0.4-final`**.
Resolve its exact commit with `git rev-parse v0.4-final^{commit}`. The last
runtime/evidence checkpoint is `64ffdb0e180500bd67e9a7f53bae93f142d13256`;
the final release commit adds reports and evidence indexing.
The generated source archive and SHA-256/commit manifest are in `artifacts/`.
They contain tracked source/evidence, not installed dependencies or build output.

## PASSED

| Area | Verified outcome |
|---|---|
| Build | All nine ROS packages built at version 0.4.0; dependency pins retained |
| Automated regression | 56 colcon entries: 51 distinct Python cases + 5 CTest wrappers; zero errors/failures/skips |
| V0.3 mission regression | Single-PX4 synthetic target/HOLD/RETURN and no-target timeout/RTL; landed/disarmed/COMPLETE |
| Two-PX4 isolation | Unique namespaces, instance/system/DDS IDs, map origins, independent commands and source-correlated ACKs |
| Two-PX4 mission | One observer while the other searches; separate returns and correct all-active completion |
| Four/eight structure | All distinct telemetry/readiness/GCS links; no premature launch |
| Eight-PX4 flight | 236.8 s accepted SPLIT run: eight ready/armed/Offboard/searching, one launch each, all landed/disarmed/DOCKED before COMPLETE |
| Deployment | SINGLE logic waypoint 0 and real eight-PX4 SPLIT waypoints 0/1; no duplicates; configured docking total |
| QGC UI | Distinct Vehicle 1/2 cards, modes, arming and altitudes, selected battery/map/motion; IDs 1–8 verified by backend probes |
| Camera | Real Gazebo RGB Image + CameraInfo, cv_bridge and increasing sensor stamps; local 640×480/10 Hz model |
| OpenCV/geometry | Real orange dummy detections projected via camera rays, measured PX4 attitude/map pose and flat ground; geometry tests pass |
| Real perception mission | Persistent Target, one observer, physical standoff, HOLD/RETURN, measured landing/disarm/COMPLETE |
| Two-camera fusion | Two real camera witnesses for one tgt_001; full mission 163.7 s with 38/53 detections and one assigned observer |
| Moving dummy | 104.0 s live PX4/Gazebo mission, 186 accepted set_pose updates, 771 images, 31 detections, stable ID and velocity, HOLD/RETURN/COMPLETE |
| Health/reassignment | Genuine simulated PX4 battery below 20%; one ROS return request; same target transfers after confirmed return; mode-loss recovery yields to PX4 |
| Two targets | Two separated synthetic targets, distinct IDs and observers; both HOLD/RETURN/land/disarm and COMPLETE |
| Basic separation | Bounded cells/altitude layers; 678 fresh-pose samples, minimum horizontal 4.21 m and 3D 4.47 m in eight-flight run |
| RViz / examiner | Global Status OK, readable IDs/state/battery/target/confidence/HOLD, measured trail, standoff ring and assignment; visible camera demo completes |
| Independent logic | Eight logical UAVs, SINGLE deployment and two operator target workflows, 780 marker arrays, all-eight docking/COMPLETE in 160.7 s |
| Static/source contracts | 67 Python, 23 XML/SDF/model-config, 14 YAML, 24 shell; 11 launch descriptions; msg/srv/action definitions identical to V0.3 |

Detailed commands and evidence are in [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md),
[docs/V0_4_VALIDATION.md](docs/V0_4_VALIDATION.md) and
[V0_4_TEST_RESULTS.md](V0_4_TEST_RESULTS.md). The release evidence index is
[docs/validation/v04_release_gates.json](docs/validation/v04_release_gates.json).

## Packages and files

Package boundaries remain unchanged. Perception adds a separate real PX4
OpenCV backend and camera geometry; targets add descriptive velocity/fusion;
swarm adds fresh-state/battery/witness filtering and confirmed-return release;
mission adds one-shot low-battery return; simulation extends the existing PX4
adapter and adds lightweight cameras, target motion and a UGV display proxy;
core adds examiner markers; bringup adds profiles, identity TF and validation
integration. Wildlife vehicles retain their established behavior. Interfaces
only receive release metadata; typed definitions are frozen. All nine package
versions are 0.4.0.

The exact added/modified paths relative to v0.3-final are listed in
[docs/V0_4_FILE_MANIFEST.md](docs/V0_4_FILE_MANIFEST.md). No historical package,
validation evidence or useful Git checkpoint was removed. The uncommitted
handoff work was preserved and committed in coherent continuation checkpoints.

## V0.3 features preserved and fixes found

Readiness-aware active deployment, queued LAUNCH, early pause/abort overrides,
NED/ENU spawn-origin transforms, relative home altitude, bounded search,
configured docking totals, source-correlated ACKs, retries/recovery, fault
reporting, pinned dependency paths, owned-process cleanup, PX4 world, seeded
logic, QGC helpers, HOLD then later RETURN, no-target RTL and correct COMPLETE
semantics remain exercised by regression and live evidence. No second UAV or
mission FSM was created.

The integration work exposed these defects/limitations and made small fixes:

- Multi-source camera assignment could happen before fusion and create another
  identity as viewpoints changed. The two-camera profile now waits for both
  witnesses and uses the previously tested 4 m association gate.
- Parallel PX4 startup caused an eight-instance sensor-readiness failure.
  Runtime startup now waits for each PX4 startup before the next instance.
- Slow simulated landing/status streams caused stale faults in the loaded
  fleet. A separate three-second limit is explicit in that profile; the
  existing two-second local-position freshness remains unchanged.
- The initial separate slow-stream default inadvertently became one second.
  A failed GUI run exposed this. The default now inherits the established
  configured timeout; the final visible missions pass.
- Measured native landing can recover home docking after a fault; confirmed
  DOCKED remains terminal across later transport loss.
- RViz lacked an explicit map TF and its initial wide/small view obscured
  labels. The identity world/map transform and larger view passed final QA.

The original high-load 1280×960/30 Hz two-camera profile is intentionally
replaced by a workspace-local 640×480/10 Hz camera model. Upstream dependencies
were not modified or upgraded. Failed attempts remain beside successful runs.

## PARTIALLY VALIDATED

Camera localization is defensible for the tested flat-ground visual dummy,
not an accuracy guarantee. The best stationary sample in the reduced-load
camera mission was 0.54 m from the configured dummy, but this is a best sample
rather than an error distribution. Image and pose are not exactly synchronized.
Moving-target velocity is a smoothed finite difference of noisy locations;
the moving probe's location error is relative to its start point, not its
contemporaneous ground truth. Standoff was exercised across stationary,
moving and reassignment scenarios; approach headings were not exhaustively
swept and the observer holds a bounded point rather than chasing motion.

Health evidence covers simulated low battery and deliberate loss of Offboard,
with unit coverage for stale state, unavailable candidates, pause/resume/abort,
retries and recovery. It does not cover every PX4 native failsafe. Search-cell
separation is validated for the recorded profile, not arbitrary paths or
concurrent close-target approaches. QGC UI QA covers two relevant aircraft;
every eight-vehicle settings/status page was not individually inspected.

Performance was sampled on an i5-13420H / roughly 16 GB machine. The accepted
fleet's return-phase Gazebo sample had real-time factor about 0.40; process
CPU is a lifetime average and RSS is KiB. Internal ROS telemetry arrival gaps
are measured in the passing flight; the separate late rate probe is marked
NO_DATA. This is not an exhaustive ROS bandwidth or host-capacity benchmark.
The camera-only short sample delivered 10.31 fps. No YOLO inference rate exists.

## NOT TESTED

Eight-camera or eight-YOLO flight, YOLO/object-class accuracy, physical UGV
navigation and tray-contact docking, exact sensor-time localization,
calibrated target speed/error, broad terrain/camera conditions, arbitrary
collision avoidance and comprehensive hardware/native failsafe coverage.
YOLO was optional and remains unimplemented; no dependency was added for it.

## KNOWN LIMITATION / warnings

The UGV is a logical deployment controller with a collision-free Gazebo visual
mirror. DOCKED is measured home landing/disarm accounting, not tray contact.
Identical nearby objects can merge inside the association gate. A paused/stale
observer retains its reservation until a confirmed return or explicit
recovery. Native PX4 remains responsible for flight control and failsafes.

The scale profile is deliberately camera-free and runs below real time on
this host. Rebuilds during flight and the original camera load are unsuitable.
QGC may need a fresh instance after many fleet restarts. Its native preflight
warnings are not hidden. Gazebo's ground is dark; RViz provides the clearer
mission view. After successful logic COMPLETE, forced shutdown still prints
legacy rclpy interrupt traces and the daemon keyboard console can abort during
interpreter finalization. All owned mission processes stopped; typed operator
services and live behavior passed. Graceful console shutdown remains follow-up
work, rather than a passed shutdown-quality claim.

## Recommended next milestone

V0.5 should first make operator-console shutdown clean, then add timestamp-
paired pose/image localization and contemporaneous moving-model ground truth
for reproducible error distributions. Pressure-test close-object association
and mission-level proximity warnings before expanding to more cameras.
Physical UGV navigation/docking and YOLO require separate scoped milestones.
