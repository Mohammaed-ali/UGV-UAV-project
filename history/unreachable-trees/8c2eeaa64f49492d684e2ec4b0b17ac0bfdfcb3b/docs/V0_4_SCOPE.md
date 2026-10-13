# V0.4 scope and release gates

V0.4 continues `v0.3-final` in the same nine-package ROS 2 Jazzy workspace.
The typed interfaces and existing PX4 adapter/mission FSM remain authoritative.
This is academic, non-contact observation: PX4 stabilizes the vehicles and
owns native failsafes; ROS manages deployment, search, targets, standoff and
human operator decisions. No payload, contact or pursuit behavior is added.

Implemented scope includes independent PX4 identities/commands/telemetry,
real Gazebo down-cameras, OpenCV pixel-to-map ground-plane localization,
persistent tracking and multi-source fusion, descriptive target velocity,
health exclusion and confirmed-return reassignment, lower-load camera
profiles, separate fleet search cells, and examiner visualization.

The eight-aircraft demonstration uses selected lightweight backends: no
cameras or YOLO on the fleet. Camera missions use one or two 640×480/10 Hz
cameras. YOLO is optional and unimplemented. The logical UGV continues to
control waypoint/deployment timing; its new Gazebo proxy is a visual mirror,
not a physical navigation or tray-contact controller. DOCKED is a simulated
landing/disarm accounting state.

Release requires the original brief's applicable gates: regression; two-PX4
isolation and mission; four/eight structure; multi-vehicle QGC; real camera,
OpenCV and map geometry; single perception mission; two-source fusion;
moving target; health/reassignment; basic separation; multi-camera mission;
and final examiner visual QA. Gate evidence is in V0_4_VALIDATION.md.
An attempted fleet flight or an open RViz window alone is not a PASS.

Remaining uncertainty is stated separately from successful demonstrations:
exact sensor-time pose synchronization, general localization/velocity
accuracy, distinguishing visually similar targets inside the association
gate, physical UGV arrival/docking, comprehensive native failsafe coverage,
and production collision avoidance remain outside the claims of this release.
