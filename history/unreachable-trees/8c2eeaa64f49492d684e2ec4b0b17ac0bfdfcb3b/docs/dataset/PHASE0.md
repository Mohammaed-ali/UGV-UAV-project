# V0.5-B1 Phase 0

Source baseline: `v0.4-final`, `949baba06fea505147b5a1cff11a53bb523827a4`.
Work remains in the existing `wildlife_ws_ros2_jazzy_v0_3` primary repository,
branch `codex/v0.5-synthetic-dataset`. The tag is unchanged. The original
working tree was clean on `codex/v0.4-development` at the same commit.

## Gate 0 — PASSED

Read README, ARCHITECTURE, V0_4_BUILD_REPORT, V0_4_TEST_RESULTS,
V0_4_VALIDATION, V0_4_CAMERA_GEOMETRY and DEMO_GUIDE, simulation worlds,
camera SDF, perception geometry/configuration, bringup profiles, set_pose
usage, validation helpers and static/release evidence before implementation.
`scripts/check_prereqs.sh` passed; `scripts/build_ros.sh` built nine packages.
`source scripts/environment.sh; colcon test --base-paths src --executor sequential;
colcon test-result --verbose` returned 56 entries, zero errors/failures/skips.
Static checks parsed 67 Python, 23 XML/SDF/config, 14 YAML and 24 shell files,
and generated all 11 launch descriptions. Evidence: `evidence/baseline*`.
No ROS package or typed contract is changed by this tool.

## Gates 1–2 — PASSED, with known limitations

The default shell did not expose `gz`; sourcing the existing Jazzy project
environment does. Installed versions: sim **8.15.0**, sensors **8.2.2**,
rendering **8.2.3**, transport **13.6.0**, msgs **10.4.0**. Existing Python:
numpy 1.26.4, OpenCV 4.6.0, PyYAML 6.0.1. No package was installed or upgraded.
Rendering uses **Ogre2 / EGL headless / OpenGL 3+**; the observed renderer is
NVIDIA GeForce RTX 4050 Laptop GPU, driver OpenGL 4.5.0 NVIDIA 595.91.07.
The default sandbox hides rendering devices and blocks transport sockets;
the authorized probes ran with sandbox escalation, independent of ROS/PX4/QGC.

Tested invocation:

```bash
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/phase0.py
# Owned child: gz sim -s -r --headless-rendering -v 2 <world.sdf>
```

The separate sensor spike received RGB, native **visible 2D**, **full 2D**,
**oriented 3D**, **semantic segmentation** and **instance segmentation**.
All four class labels were observed in the actual transport output.
Instance pixels were `[instance_low_byte, instance_high_byte, class_label]`;
semantic pixels repeated the class label across RGB. These capabilities were
tested on this installed system, not inferred from another Gazebo release.
Evidence: `evidence/native_sensors.json`, log, PNG and the pinned spike world.
The installed `boundingbox_camera.sdf` / `segmentation_camera.sdf` examples
and headers were inspected. References: [sensors 8 segmentation](https://gazebosim.org/api/sensors/8/segmentationcamera_igngazebo.html),
[sim 8 headless rendering](https://gazebosim.org/api/sim/8/headless_rendering.html).

Selected primary method: **native visible 2D bounding-box camera**. Its integer
maximum corner is treated as inclusive and converted to half-open pixel
coordinates before clipping/YOLO normalization. Secondary method: independent
pinhole projection of original primitive surface geometry, transformed by
read-back simulator poses. It represents a full silhouette, so it legitimately
differs from visible boxes under occlusion. Neither method invokes a detector.
Native class labels do not expose stable instance IDs. Boxes are associated
with non-interpenetrating target instances using class and projected geometry;
unexplained native boxes cause rejection. No pixel visibility fraction is claimed.

The deterministic alignment proof has one example per class for centered,
near, far, edge/truncation and partial occlusion, plus all four classes together:
**21 cases**. Actual camera/target poses, matching image/annotation timestamps,
native labels and YOLO exports are checked. Contact sheet and full-resolution
overlays were visually inspected. Evidence: `evidence/phase0/alignment.json`,
`alignment/contact_sheet.jpg`, per-case metadata and labels. Raw RGB/overlays
are retained locally; the contact sheet is tracked. Small targets require
full-resolution inspection.

## Fixed camera and operational altitudes

Read directly from the unmodified V0.4 `mono_cam/model.sdf`: 640×480, 10 Hz,
horizontal FOV **1.74 rad**, vertical FOV derived from square pixels,
`fx=fy≈269.968`, `cx=320`, `cy=240`, clipping **0.1–100 m**, no configured noise.
Gazebo +X is forward, -Y image right, -Z image down. The freely positioned
rig records the actual optical-center pose and AGL; it needs no UAV body or
dynamics. RGB/box sensors share a link, zero relative pose, intrinsics, clips
and rate. Live CameraInfo matches the source-derived values within 0.01 px.
No intrinsics/resolution/FOV randomization occurs.

Camera search profiles use 10 m and 15 m. Logical standoff uses search altitude
plus 3 m (13/18 m); fleet altitude layers 10+1.5*i are camera-free. The dataset
retains 10/20/30/40 m and adds **15 m** for the actual two-camera profile.
The feasibility table additionally evaluates 13/18 m; these do not become
separate dataset quotas because 15/20 m already cover nearby observation
scales. Nominal buckets get ±1 m jitter; off-nadir 0/10/20/30° gets ±2°,
clamped to zero at nadir. Yaw is continuous uniform over [0,360°).

`evidence/phase0/pixel_size_feasibility.csv` evaluates class × altitude ×
angle × near/medium/far/edge, across eight footprint directions and four
object yaws. It reports min/mean width, height and area, with flags below
3 px. These are geometric estimates, not detector performance measurements.
**50 of 448 cells** had a below-threshold side in the initial measured table.
Decision: retain all factor levels, account for tiny targets with `ignored_tiny`,
and require normal placements to fit the image. Edge challenges explicitly
permit truncation. Usable footprint radii include ground ray intersection and
a conservative far-clip bound, rather than fixed metric distance bands.

## Assets and scale

No mutable Fuel or internet asset download is required. The pinned pool has
15 original procedural targets: person 4, car 4, truck 4, bus 3; 16 original
seeded background textures; and nine original distractor/occluder structures.
Checksums, geometry bounds, dimensions, authorship, creation date, source URI,
license and split eligibility are recorded in
`tools/synthetic_dataset/assets/manifests/assets.json` and `.csv`.
The original assets are dedicated under CC0-1.0, separately from upstream code.
No external model/texture is incorporated. The source builder can regenerate
the pinned pool; ordinary generation only verifies and reads it.

People have human-height geometry (~1.68–1.88 m); cars use distinct body/cabin
dimensions (~4.2–4.9 m length); trucks include open bed, box and tanker forms;
buses are ~10.5–12.8 m with differing body/roof geometry. Actual dimensions
include wheels and attachments and are recorded, not assumed. The exact
minimum geometry Z is normalized to zero; actual world placement is read back.
These are recognizable low-detail synthetic representations, not realistic
human/vehicle meshes. Human variants share a template: **no independent
held-out person model is claimed**. One structurally different car/truck/bus
and one texture per background family are test-only. Recoloring is not counted
as independent model diversity. Texture holdout tests procedural patterns,
not a new real terrain domain.

## Scene updates, synchronization and benchmark

Preloaded targets move through `set_pose_vector`; unused instances move to a
staging region outside the frustum. Backgrounds are preloaded at separated
zones, avoiding runtime material mutation/downloads. A directional light uses
the existing `light_config` service; four families change elevation, azimuth,
color and intensity. `lighting_changes.json` independently demonstrates color/
intensity changes with the same camera and targets. An 8 m wall is placed
up-sun with conservative target clearance for deliberate cast shadows. Trees,
crates, barriers and supported canopies supply additional shadows/occlusion.

Each capture waits for read-back poses, then at least three sensor periods
of simulation settling, then a fresh RGB/native-box pair within **0.001 s**.
The measured pairs have zero timestamp delta. Commanded poses are stored
separately from actual simulator poses. Static world geometry avoids the
cross-clock PX4 localization limitation in the mission pipeline.

Failed attempts are retained: default sandbox socket creation failed; using
blocking transport requests on the subscriber client intermittently failed
after several scenes at RTF 0, 8 and 1. Separating the request client into a
private persistent process resolved this observed failure. This is an
empirical workaround for the installed Python bindings, not a proof of their
internal root cause. An exploratory scene-message import also hit a generated
protobuf message registration error; it is excluded from the capture path.
Some Ogre2 warnings and an entity-0 visualization warning remain in logs;
actual RGB/box/pose evidence and lighting changes are validated independently.

The representative 60-frame benchmark uses fixed 640×480, shadows, clutter
and 1–8 targets, with one Gazebo process and finite requested RTF 8. Initial
measurement: ~443 accepted/attempted frames per minute. The final retained run
measured **416.645 frames/min**, average PNG **200,392.633 bytes**,
**1,391,542.197 bytes/s** image writes, **911,120–911,252 KiB RSS**.
Process CPU samples were **125–177% lifetime CPU**, not whole-host utilization.
`evidence/phase0/benchmark.json` contains final
measurements, process samples and the extrapolation. Planning estimate for
10,000 images: **1,440.076 seconds (~24 minutes)/2,003,926,333 bytes RGB**,
plus metadata and QA. Pilot measurements
will replace this estimate before full generation. No parallel renderers are used.

## Limits and next gate

**KNOWN LIMITATION:** Synthetic Gazebo imagery is not equivalent to real
aerial-camera imagery. Procedural materials and silhouettes do not establish
real-world accuracy, VisDrone-equivalent realism, or sim-to-real success.
Shadow presence is demonstrated; photometric realism and a calibrated pixel
occlusion fraction are **NOT TESTED**. The 200-frame smoke dataset subsequently
passed validation and visual QA. Work stopped during Gate 4: two 50-frame runs
have identical RGB/YOLO/scenario bytes, but exact comparison of raw readback
metadata rejects equivalent quaternion signs and floating-point roundoff.
Gate 4 is **PARTIALLY VALIDATED**, with its comparator repair pending.
See [the continuation handoff](V0_5_B1_HANDOFF.md) for the precise failure,
repository state and remaining sequence. Crash/resume, pilot, 300-frame audit,
full dataset and final V0.4 regression have not been run.
