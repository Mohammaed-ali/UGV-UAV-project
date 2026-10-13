# V0.4 release handoff — 2026-10-04

Primary workspace: `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
Branch: `codex/v0.4-development`. V0.3 baseline: `v0.3-final` / `8ca1e9d`.
Final V0.4 release identity: **`v0.4-final`**; resolve the exact release commit
with `git rev-parse v0.4-final^{commit}`. Runtime/evidence checkpoint:
`64ffdb0e180500bd67e9a7f53bae93f142d13256`. The release adds the final reports.
The original brief remains at
`/home/mohammed-ali/.codex/attachments/6f037b0f-202e-4781-ad34-a3ef900b1863/Pasted text.txt`.
This replaces the unfinished handoff after completing its applicable gates.

## Preserved history and continuation

Nine ROS packages and original message/service/action definitions are retained.
No second UAV or mission FSM. Dependencies remain PX4 v1.17.0 d6f12ad1,
px4_msgs 86d8239e and XRCE agent 73622810 under
`/home/mohammed-ali/Downloads/wildlife_px4_dependencies`.
V0.2 and older folders were not rebuilt or substituted.

Original checkpoints: 95dacc0 isolation, bc8b6f2 two mission, f911234 stationary
fleet, 6d72e5b real camera. Continuation: e14483b tracker/health, dbf8b09 reduced
camera/two fusion, dd24278 live moving target, 0b60315 health/two targets,
64ffdb0 eight-flight/full-camera/examiner/logic verification.
The initial uncommitted work was preserved and committed; failed evidence
was retained. Reports identify validated scope rather than all possible use.

## Accepted gates

Final build: nine packages at 0.4.0. Final test result: **56 entries, zero
errors/failures/skips** (51 distinct Python cases plus five CTest wrappers).
Static: 67 Python, 23 XML/SDF/config, 14 YAML, 24 shell; 11 launch imports;
typed definitions match V0.3.

Single-PX4 synthetic target/no-target and two-PX4 independent/control mission
pass. Four/eight stationary structure pass. Two-camera fusion and full mission
pass with one persistent tgt_001 and both witnesses; the full profile waits
for two witnesses before assignment. Real images use **640×480/10 Hz** local
mono_cam. Preserve it: original 1280×960/30 Hz two-camera load lost telemetry.

Moving visual target flight passed (104 s), including accepted Gazebo motion,
real images, persistent ID/velocity and operator/landing/COMPLETE. Velocity
and start-relative error are descriptive, not contemporaneous accuracy.
Observer remains bounded; no pursuit.

PX4 simulated low battery and deliberate mode loss passed with safe same-ID
reassignment only after confirmed return. Stale/PAUSED reserves an existing
observer until explicit recovery. Two separated synthetic targets passed.

Eight real PX4 SPLIT flight passed (236.8 s): readiness, exactly one launch
per UAV at waypoints 0/1, all-eight search, ID/ACK isolation, no PAUSED,
all landed/disarmed/DOCKED and COMPLETE. Minimum horizontal/3D separation
4.21/4.47 m over 678 samples. NO cameras on this profile.
Existing local-position freshness is **two seconds**, not one. The fleet
explicitly allows three seconds for slower status/landing; default inherits
the configured position timeout. Retain this distinction.

QGC visually showed distinct Vehicle 1/2 cards/modes/altitudes/battery. IDs
1–8 have backend/GCS evidence; every eight-vehicle UI page was not inspected.
Final visible real-camera examiner run passed (144 s) with RViz Global Status
OK, readable observer/target/HOLD/standoff/assignment/trail. Gazebo shows the
orange dummy and UGV visual proxy. Eight logical UAVs independently passed
SINGLE/operator/COMPLETE (160.7 s). Evidence is under `docs/validation/`.

## Reproduction and limits

Read README.md, ARCHITECTURE.md, docs/DEMO_GUIDE.md, docs/V0_4_VALIDATION.md,
V0_4_BUILD_REPORT.md and V0_4_TEST_RESULTS.md. Use existing helper scripts;
keep QGC running, one PX4 runtime at a time, logs in /tmp, local loopback
transport, and do not rebuild during flight. Helpers clean only owned process
groups. A QGC instance remains open; no owned flight/mission runtime remains.
Exact Git source archive/checksum manifest is generated in `artifacts/`.

The UGV is logical with a display-only, collision-free Gazebo mirror.
DOCKED is measured simulated home landing/disarm, not physical tray contact.
Exact image/pose synchronization, calibrated localization/velocity,
comprehensive PX4 failures, close identical-object separation, general
collision avoidance, physical UGV navigation and eight-camera flight remain
unverified. YOLO is optional/unimplemented. Performance evidence is a local
sample (return-phase RTF about 0.40), not a capacity guarantee. The late rate
probe is NO_DATA; valid receipt gaps are in the passing flight JSON.

After logic COMPLETE, forced shutdown still prints legacy rclpy interrupt
traces and the optional daemon stdin console can abort at finalization.
All owned mission processes stopped; this is a known shutdown-quality issue.
First V0.5 task: make console shutdown clean, then add timestamp-paired
localization and moving-model ground truth before expanding camera scale.
Preserve v0.4-final and branch follow-up work; do not silently broaden claims.
