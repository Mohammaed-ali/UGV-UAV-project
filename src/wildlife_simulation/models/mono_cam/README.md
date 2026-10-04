This is the pinned PX4 v1.17 `mono_cam` SDF model, copied into the V0.4
workspace with only image size (640×480), update rate (10 Hz), far clip and
visualization changed. Its camera mount, link, sensor and optical geometry
remain the same. The included PX4 BSD-3-Clause license applies to this model.

The camera launch scripts place this directory ahead of the pinned PX4 models
in `GZ_SIM_RESOURCE_PATH`; ordinary V0.3 x500 runs are unaffected. This profile
was added after two default 1280×960, 30 Hz cameras saturated telemetry and
triggered PX4 failsafe during the first fusion attempt.
