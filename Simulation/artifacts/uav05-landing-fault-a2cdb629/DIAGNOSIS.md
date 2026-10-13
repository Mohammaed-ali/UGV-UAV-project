# UAV05 landing fault

Run: `a2cdb629-d678-4158-81e4-63119ee854ea`, stop Bravo.

UAV05 launched at 359.82 simulation seconds, confirmed a person from camera
images at 400.80 s, and returned at 415.86 s. It acquired its assigned AprilTag 5
and began descent at 432.74 s. The controller retried tag acquisition at 469.32
and 473.70 s, then faulted at 477.99 s with:
`Assigned landing tag stayed out of view; recovery requires operator`.

This was a landing-control coordinate mismatch. Image-derived tag coordinates
are transformed with the camera's measured Gazebo pose, but the landing controller
subtracts PX4's position estimate from them. The two world positions differ.
At 464.38 s the controller reported 0.0152 m of alignment error while the measured
physical error was 0.1411 m. At the first recorded tag-loss sample (467.47 s),
physical error was 0.1240 m and image age only 0.07 s. Native PX4 logs independently
show approximately 0.12–0.16 m of horizontal estimator/frame discrepancy in the
final approach. Height disagreement also delayed the existing landing handoff.

Projection of the recorded geometry puts tag corners at image rows 504–512 in
a 480-row camera when the tag first disappears; later retries repeat this
pattern. This clipping explanation is an inference from calibrated camera and
recorded physical geometry. The historical failure images were not recorded;
post-fault raw and annotated images have been preserved. The recorded detector
results confirm fresh frames without tag 5 during these intervals.

After commanding a climb for the last reacquisition attempt, the mission entered
FAULT and stopped advancing its state machine. UAV05 remains armed in Offboard
hover above its extended tray; tag 5 is visible again from that higher viewpoint.
UAV04 waits to recover, UAV01–03 are docked, and UAV06–08 remain stored. Physics
and PX4 telemetry are still healthy. The faulted mission has not been reset.

The correction needed is to use the tag's camera-relative displacement for
alignment, apply that displacement in PX4's control frame, and reset cached
descent targets on a retry. Increasing the retry count would repeat the same
misalignment. No controller change has been applied in this diagnostic turn.

Evidence: `state.json`, `config.json`, `uav05-flight.ulg`,
`position-frame-analysis.json`, `final-approach-analysis.json`, post-fault camera
images and `runtime-logs/`. An invalid initial calibration attempt is retained
separately and clearly marked; it is superseded by the first-Offboard calibration.
