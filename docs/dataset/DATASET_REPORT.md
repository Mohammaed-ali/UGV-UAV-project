# V0.5-B1 — Synthetic Gazebo aerial detection dataset

**V0.5-B1 PASSED: Gates 0–10 complete.** The final dataset contains **10,000 accepted frames: 8,000 train / 1,000 validation / 1,000 test**, with revised human sampling and improved licensed assets. The full validator, visual review, annotation audit, determinism, crash/resume and V0.4 regression pass. No detector training was performed.

## Source and scope

The primary workspace remains `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`, on `codex/v0.5-synthetic-dataset`. Frozen `v0.4-final` is `949baba06fea505147b5a1cff11a53bb523827a4`. The continuation began at `947cecb5ccaf607b7466ed8dff29651efe730f9f`; the revised smoke, determinism, crash/resume, pilot and full captures use generator revision `796c48e0622f9ee70efd96e47a79a4075e9a7dbd`.

The generator is offline tooling under `tools/synthetic_dataset/`, outside the nine ROS packages. No V0.4 runtime `src/`, `scripts/`, typed interfaces, PX4 adapter, mission, detector, tracker or UGV behavior is modified. Dataset assets are not dependencies of existing demos. No YOLO training, Ultralytics installation, VisDrone download, ROS YOLO integration, moving/video collection or PX4 flight collection is part of this milestone.

The original [master prompt](V0_5_B1_MASTER_PROMPT.md), [historical handoff](V0_5_B1_HANDOFF.md), [human sampling requirement](HUMAN_SAMPLING_REQUIREMENT.md) and [higher realism addendum](HIGHER_REALISM_REQUIREMENT.md) are preserved. [Continuation results](CONTINUATION_RESULTS.md) retain failures and minimum corrections. Earlier primitive datasets remain technical evidence and are not accepted against the revised fidelity requirements.

## Architecture and annotations

Installed Gazebo Harmonic **8.15.0**, Ogre2, native transport13/msgs10 Python bindings and the existing Jazzy environment render one private headless world. Actual Ogre2 diagnostics identify NVIDIA RTX 4050 / GL 4.5 rendering. No GUI, ROS bridge, flight controller or trained detector is needed. The world preloads static target pools, photographic terrain zones and outdoor context; pose-vector and light-config services change each intentional still scene. A persistent separate service worker keeps blocking Gazebo RPC out of subscriber callbacks, addressing observed installed-binding stalls. Unique transport partitions and recorded owned process groups isolate cleanup.

Native **visible 2D bounding boxes** are primary ground truth. Feasibility independently proved RGB, visible/full 2D boxes, 3D boxes and semantic/instance segmentation. Visible boxes match the exported image and handle partial occlusion; full boxes and geometry silhouettes include hidden parts. Simulator labels 10/20/30/40 map to YOLO **0 person, 1 car, 2 truck, 3 bus**. No vision algorithm infers class labels.

Bounding-box maxima from Gazebo are inclusive and become half-open pixel bounds before clipping and YOLO normalization. Ordinary same-class matching uses IoU ≥0.01. A below-cutoff native sliver can associate only if it overlaps exactly one same-class full projection and is contained within 1 px raster padding. Ambiguity, unexplained labels and invalid geometry still reject. This fixes the preserved first-pilot failure without enlarging labels. Private unique-per-instance simulator labels independently checked all 50 lowest-IoU revised-pilot associations.

Secondary QA freshly projects the extreme vertices of each rendered mesh convex hull (or exact primitive geometry) using recorded actual target and camera poses. Perspective projection extrema are preserved by the hull representation. This method is independent of native raster boxes and includes the full unoccluded mesh. Box IoU is **not** a pixel visibility fraction. A clipped full-mesh bounding rectangle can exceed the bounding rectangle of the clipped visible silhouette, even without occlusion.

Objects are exported only if their native box is at least 3 px on each side and 9 px² area. All target instances remain in metadata with `labelled` or explicit tiny/occluded/outside ignored state/reason. An intended positive scene may have empty labels when every target is ignored; it is counted separately and never silently relabelled as an empty scene. True negative and distractor-only frames have empty target lists and labels. No unvalidated visibility fraction is fabricated.

## Fixed camera and capture evidence

Camera values come from the unchanged repository `mono_cam/model.sdf`: **640×480, 10 Hz, horizontal FOV 1.74 rad, clip 0.1–100 m**; pinhole `fx=fy=269.968184`, `cx=320`, `cy=240`, vertical FOV approximately 1.453402 rad. Camera axes are +X forward, -Y image-right, -Z image-down in world ENU. Live CameraInfo matches these intrinsics and image size. Camera source SHA256 is `7ad6bc5ea6d3e708149246edea6219aebba80f9773e59ea9a7ca78f067a9c765`.

Nominal altitude buckets are 10/15/20/30/40 m with ±1 m jitter; 15 m preserves validated V0.4 profiles. Off-nadir buckets 0/10/20/30 degrees use ±2 degrees jitter, with valid zero-nadir handling, full 0–360 degree azimuth/object yaw and zero roll jitter. Ground reference and realized poses are recorded. Difficult altitudes, angles and distance levels were retained rather than silently removed.

Capture verifies realized camera/target pose against commanded state (1 mm position and 1e-5 orientation tolerance), then waits at least three fresh 10 Hz frames. RGB and native boxes must be newer than the scene readback/settling interval and synchronized within 1 ms. Revised pilot measured zero timestamp delta, minimum 0.3 s settling and max actual/commanded position error 2.04e-12 m. [Corrected alignment](evidence/human_realism_alignment_v2/report.json) passes 21 center/near/far/edge/occluded/multiple-object cases. Its 448-cell pixel table uses one representative mesh per class across seven altitudes (10/13/15/18/20/30/40 m), four angles and four distance bands. It retains 26 below-threshold configurations with explicit ignored handling; it is not an exhaustive asset-variant table.

RGB anti-aliasing 4 is placed in the installed SDF-supported `camera/image` element; bounding-camera AA stays 1. A 40-scene AA ablation produced exact native box/YOLO bytes for AA 1 versus AA 4, with measured short-probe throughput 479.92 versus 377.34 frames/min. AA 4 is retained; final capacity decisions use the longer pilot/full run. Historical entity-0 visualization and bbox-AA warnings remain in logs; capture/pose/labels are independently verified.

## Assets, scale and improved fidelity

The pinned manifest contains **44 assets**: 8 clothed human derivatives, 4 cars, 4 trucks, 3 buses, 16 terrain materials and 9 unlabelled context structures. [ASSETS_V2.md](ASSETS_V2.md) documents source/revision/license and limitations; JSON/CSV manifests record local paths, SHA256/dependency checksums, authors, scales, measured bounds, polygon counts and split eligibility.

Humans use retained CC0 MakeHuman hm08 geometry, with realistic head/torso/limb silhouettes, static lowered-arm variations, adult heights roughly 1.68–1.89 m, body proportions and clothing/skin/hair appearance. All eight derivatives share **one template**; no independent human model holdout is claimed. Cars/trucks use retained CC0 Kenney Car Kit 3.1 shaped cabin/wheel/cargo meshes. Original CC0 coach meshes have beveled bodies, windows, wheels and roof equipment. Mesh axes are normalized to meters and exact minimum Z=0. Measured full-mesh lengths are 4.10–4.95 m for cars, 6.10–7.60 m for trucks and 8.26/11.56/12.46 m for buses (including mirrors). Geometry footprint separation and actual pose readback prevent floating/embedded target placement.

Twelve CC0 Poly Haven photographic source materials supply albedo/GL-normal/roughness maps. Deterministic 80 m mosaics repeat over 240 m planar terrain with irregular grass/dirt transitions, road margins and worn markings. Missing upstream physical texture scale is explicitly approximated. Context includes faceted tree crowns, slatted crates, concrete barriers, supported corrugated canopies and masonry shadow walls. Directional sun families morning/noon/evening/shadow use applied light-config parameters, subdued warm colors and ambient balance. Shadow scenes include local cast shadows and mixed lit/shaded people.

The first upgraded smoke was visually rejected for reflected/inward face winding and heavy material fragmentation. Corrected outward winding and palette clustering retain visual structure while reducing vehicles to 13–14 material meshes. The corrected 60-frame alignment benchmark improved from roughly 114 to 444 accepted/min. Closed coach surfaces and orientation/material budgets have regression tests. All 40 original procedural asset files/checksums remain preserved in the legacy manifest.

Qualitative smoke/pilot review explicitly passes human recognizability, vehicle recognizability, terrain, lighting, shadows and overall scene plausibility. Both stages inspect 100 representative overlays, all eight dedicated best/human/single/multi/mixed/shadow/occluded/weak sheets and native larger-human examples. Selection heuristics only choose review candidates; they are not automatic realism scores. Revised images are improved **simplified synthetic imagery**, not photorealistic or equivalent to true aerial photographs. Detailed faces, independent body families, vegetation, real traffic/crowd patterns, atmospheric lighting and terrain relief remain absent/simplified.

The fixed 100 m clip and finite 240 m terrain expose environment background at some high/oblique corners: 111/2,000 pilot frames, maximum 5.53% of pixels. An analytical ground-ray/patch/far-plane diagnostic explains the boundaries; difficult 30/40 m, 30 degree levels remain retained. Targets use a conservative far-bounded footprint. Final measured artifact frequency is reported below.

## Human-priority sampling and splits

Each sample is a newly generated intentional scene, varying camera pose, target placement/yaw/appearance, lighting, terrain, crowd composition, context and occlusion. Explicit largest-remainder quotas replace reliance on random human occurrence. TRAIN requests 60% human-positive, 20% vehicle-only, 10% distractor-only and 10% empty. Val/test independently request 30/50/10/10. These evaluation proportions are an explicit synthetic mix, not measured real-world prevalence.

Within TRAIN human requests, 45% are single and 55% multi. Multi requests allocate 40% to 2–3, 35% to 4–6, 20% to 7–10 and 5% to 11–14 people. Eval human scenes request 60% single / 40% multi. Quotas are configurable in the existing YAML, with 5 percentage-point absolute acceptance tolerance applied to actual exported visible-person composition/count/distance fractions. Crowds have conservative footprint separation plus 0.4 m margin and independently varied yaw. Scattered/loose-group/roadside placement weights are 35/35/30%; roadside attempts prefer margins but can widen placement while retaining the drawn distance band. These requests do not guarantee a measured real crowd-layout distribution.

Person-instance distance quotas are 30% near / 30% medium / 30% far / 10% edge. The draw is retained across retries; human placement cannot drop a person or silently change band. Distance means ground-plane radial fraction of the usable footprint around optical-axis ground intersection: near [0, .35), medium [.35, .70), far [.70, .90), edge [.90, 1]. It is not absolute slant range. Actual horizontal/slant ranges, usable radius and normalized distance are also recorded. Far vehicles may be clipped rather than redrawn closer. Placement shortfalls are reported. Half of human scene requests add 1–3 vehicles, preserving mixed human/car/truck/bus coverage. Mild/moderate occlusion requests are 15/5%, with 80% none; incidental context/vehicle/person occlusion remains possible under none.

Train/val/test are 80/10/10 by independently seeded scene families; each composition has balanced altitude/angle/background/light schedules. Count is part of the sampling schedule and resume identity. Scene specification hashes, scene IDs/families and image hashes are checked for uniqueness and split leakage. No images are duplicated to satisfy quotas. Test-only vehicle geometry variants and index-3 photographic sources are excluded from train/val. Test-only assets: `car_mesh_3`, `truck_mesh_3`, `bus_mesh_2`, `grass_3`, `dirt_3`, `road_3`, `mixed_3`. Humans reuse the template/appearance pool across splits, honestly recorded.

## Export, metadata, determinism and resume

Each accepted frame has PNG, YOLO label text, per-frame JSON and a completion marker containing content hashes. Image/label/JSON writes use temporary files and atomic rename; the marker is written last. Aggregate split JSONL, scene CSV/manifests and statistics are rebuilt from completed markers, avoiding append duplicates. An output lock prevents concurrent writers. Corrupt/incomplete frames are regenerated; valid frames are skipped. Resume requires identical count/seed/config/assets/core-code/Git revision, and removes leftover temporary files.

Per-frame metadata records seeds/scene identity, split/composition/group/count requests, camera source/live intrinsics/commanded and actual pose, altitude/angle, light/background/context, all target IDs/classes/assets/scale/commanded and actual pose/yaw/distance, native and secondary boxes, truncation, label/ignored state/reason, timing/settling/synchronization and projection IoU. Run manifests pin Gazebo/host/version, baseline/implementation revision, code/config/camera/asset hashes, licenses, count/rejections and resource timing. Source/license inputs and dependency files remain local and checksummed. Ordinary generation needs no downloads.

Current 100-frame independent replays at seed 12346 pass both standalone validators: 100/100 RGB PNG bytes, YOLO labels, commanded scenes and scenario/config/asset manifests match exactly. Strict metadata comparison permits only sign-equivalent unit quaternions and narrowly scoped absolute numerical readback tolerances: position 1e-10 m, quaternion component 1e-14, secondary projection 1e-8 px, derived IoU 1e-9. Measured maxima 1.82e-12 m, 4.44e-16 quaternion component, 6.03e-11 px and 1.39e-12 IoU are well below limits. Timing/UTC fields are scheduling-dependent and schema/type checked before exclusion. Tests accept sign/roundoff and reject meaningful scene/pose/native label changes. Original comparator failures/captures remain preserved.

The current real SIGKILL test kills after 30 committed markers and resumes to 200 under unchanged revision/config/assets/seed 76543. All original 30 marker hashes remain intact; no duplicate/corrupt/partial/orphan records or temporary files remain, all file/index counts match and the validator passes. Owned generator/Gazebo/service workers are absent afterward. See [determinism](evidence/human_determinism_100.json) and [crash/resume](evidence/human_crash_resume.json).

## Revised pilot results and annotation investigation

The revised pilot has **2,000 accepted frames: 1,600 train, 200 validation and 200 test**. It has 2,000 unique image hashes and all classes and heldout assets. Frame marginals are balanced: 400 per altitude and 500 per angle, background and lighting family. Exported label counts are 3,310 person, 1,055 car, 1,004 truck and 991 bus. All 96 ignored targets (45 occluded, 51 tiny), including 94 people, remain accounted for.

Visible people occur in **945/1,600 train frames (59.0625%)**, comprising 423 single-person and 522 multi-person frames with 3,000 person boxes. Validation and test each have 59/200 visible-person frames (29.5%). Six train frames and one each in validation/test have only ignored targets; these intended positives are counted separately. [Pilot human statistics](evidence/human_pilot_human_statistics.json) and [complete pilot tables](evidence/human_pilot_tables.md) provide all counts and size summaries.

Train human frame counts across 1 / 2–3 / 4–6 / 7–10 / 11+ visible people are 423 / 212 / 185 / 101 / 24. These bands contribute 423 / 518 / 915 / 846 / 298 person boxes. Isolated people contribute 14.1% of instances and 11+ crowds contribute 9.93%; the largest crowds do not dominate the instances. No visible 11+ crowd occurs in the finite pilot test split; this absence is reported rather than hidden.

Valid train person instances cover every altitude (620 / 645 / 562 / 603 / 570), angle (690 / 792 / 696 / 822), distance (902 near / 911 medium / 905 far / 282 edge), background (710 grass / 761 dirt / 793 road / 736 mixed), lighting family (798 morning / 805 noon / 695 evening / 702 shadow) and all eight appearances. Person yaw covers all twelve 30-degree bins, with train range 0.089–359.995 degrees. Of the human train frames, 470 also contain vehicles: 238 with cars, 256 with trucks and 251 with buses; these counts overlap.

Person pixel-area groups are very small <64 px², small 64–<1,024 px², medium 1,024–<9,216 px², and large ≥9,216 px². Train percentages are 24.6333%, 68.1333%, 7.2333% and **0% large**. Width, height and area count/min/p05/p25/median/p95/max/mean are reported by altitude, distance, angle and split. Valid 3×3 boxes and ignored boxes with a dimension below 3 px remain distinct. [Human balance/size figure](evidence/human_pilot_figures/human_balance_and_size.png) shows actual small-person and distance coverage.

The independent **300-frame annotation audit** covers all configured factors and 960 native instances. Fresh actual-pose reprojection of 966 objects exactly reproduces stored geometry. Overall visible/full IoU has median **0.95665**, mean 0.90431, p05 0.62574 and minimum 0.03350. Class medians are person 0.91934, car 0.97691, truck 0.98108 and bus 0.98500. All 50 lowest frame overlays and pixel crops were inspected. Canopy/tree/vehicle occlusion, edge clipping and raster effects on tiny people explain the tail; requested none can still have incidental occlusion. No close/better same-class spatial alternative was found. Private unique-instance native replay passes all 50 with identical visible boxes and YOLO bytes. Labels are not enlarged and difficult examples are not discarded to improve IoU. See [audit](evidence/human_pilot_annotation_audit.json), [50 investigations](evidence/human_pilot_low_iou_investigations.json), [identity replay](evidence/human_pilot_instance_identity_audit.json) and [IoU figure](evidence/human_pilot_figures/annotation_iou_distribution.png).

Pilot generation measured **397.28 s, 302.05 accepted frames/minute and zero capture rejections**. Capture-phase Python peak RSS was 189.9 MiB; Gazebo samples were about 0.81 GiB. RGB occupies 905,816,256 bytes; analyzed total was 1,009,759,903 bytes including QA. Generation timing includes startup/capture/per-frame export/shutdown and excludes aggregate validation/QA. Resource CPU percentages are process lifetime observations, not instantaneous whole-host load. These measured costs justify retaining the configured 10,000-frame target: forecast about 33.1 minutes, 4.53 GB RGB and 5.05 GB total, versus 35.25 GB available at decision time. [Recorded decision](evidence/full_target_decision.json).

## Full dataset results

Output: `datasets/gazebo_aerial_v1`, seed **12345**, manifest version **2-human-mesh**. The folder name is historical; these captures use the revised meshes/PBR configuration at `796c48e`, not the original primitive assets. [Capture manifest](evidence/full_capture_manifest.json), [full validation](evidence/full_validation.json), [full gate](evidence/full_gate.json), [human statistics](evidence/full_human_statistics.json) and [complete result tables](evidence/full_tables.md) preserve actual evidence.

| Measure | Train | Validation | Test |
| --- | --- | --- | --- |
| Images | 8,000 | 1,000 | 1,000 |
| Visible-person frames | 4,722 (59.025%) | 295 (29.5%) | 293 (29.3%) |
| Single-person frames | 2,123 | 175 | 174 |
| Multi-person frames | 2,599 | 120 | 119 |
| Labelled person instances | 15,093 | 761 | 777 |
| All person instances, including ignored | 15,520 | 779 | 797 |
| Vehicle-only frames | 1,643 | 502 | 503 |
| Distractor-only frames | 800 | 100 | 100 |
| Empty negatives | 800 | 100 | 100 |
| Intended positives with all targets ignored | 35 | 3 | 4 |
| Person + vehicle frames | 2,355 | 147 | 147 |

The actual TRAIN single/multi fraction is **44.9598% / 55.0402%** of visible-person frames. TRAIN human frames with cars/trucks/buses number 1,256 / 1,265 / 1,229; counts overlap. Validation/test independently retain less human emphasis, all vehicle classes, mixed scenes and negative/distractor examples. All four approximate composition targets and person count/distance quotas pass the configured tolerance. Human emphasis uses independent scenes, not duplicated images or repeated recolorings of one scene.

| Class | Train labels | Validation labels | Test labels | Total labels | All realized targets |
| --- | --- | --- | --- | --- | --- |
| person | 15,093 | 761 | 777 | 16,631 | 17,096 |
| car | 3,676 | 780 | 752 | 5,208 | 5,225 |
| truck | 3,547 | 689 | 703 | 4,939 | 4,942 |
| bus | 3,482 | 731 | 685 | 4,898 | 4,899 |

All **486 ignored targets** are accounted for: 279 tiny and 207 occluded; people contribute 276 tiny and 189 occluded. All 17,096 planned people were realized, including ignored instances. Placement constraints leave **354 requested vehicle slots unfilled in 255 frames**, separately recorded as `placement_shortfall` (214 train / 51 validation / 89 test); no people or distance bands were silently dropped. This is a placement shortfall, separate from the **zero capture rejections**. See [placement accounting](evidence/full_placement_accounting.json).

| Visible people per TRAIN frame | Frames | Fraction of multi-person frames | Person instances | Fraction of person instances |
| --- | --- | --- | --- | --- |
| 1 | 2,123 | single | 2,123 | 14.066% |
| 2–3 | 1,039 | 39.977% | 2,594 | 17.187% |
| 4–6 | 927 | 35.668% | 4,563 | 30.233% |
| 7–10 | 507 | 19.508% | 4,262 | 28.238% |
| 11+ | 126 | 4.848% | 1,551 | 10.276% |

Isolated people supply 14.066% of TRAIN person instances; the largest crowds supply 10.276%, so 11+ scenes do not dominate instances. Full test has five visible 11+ scenes and validation has six, addressing the finite pilot's absent test band without duplicating or repairing images afterward.

Frame marginals are exactly **2,000 per altitude**, and **2,500 per angle, terrain family and lighting family**. Valid TRAIN person-instance coverage is:

| Factor | Levels in order | Labelled person counts |
| --- | --- | --- |
| Altitude (m) | 10 / 15 / 20 / 30 / 40 | 3,037 / 3,098 / 3,110 / 2,955 / 2,893 |
| Off-nadir (degrees) | 0 / 10 / 20 / 30 | 3,681 / 3,836 / 3,802 / 3,774 |
| Distance | near / medium / far / edge | 4,540 / 4,566 / 4,556 / 1,431 |
| Terrain | grass / dirt / road / mixed | 3,739 / 3,778 / 3,862 / 3,714 |
| Lighting | morning / noon / evening / shadow | 3,808 / 3,932 / 3,746 / 3,607 |
| Requested occlusion | none / mild / moderate | 11,973 / 2,368 / 752 |

Distance fractions are **30.080% near / 30.252% medium / 30.186% far / 9.481% edge**. All eight human appearances contribute 1,788–1,946 valid TRAIN instances each. Person yaw spans all twelve 30-degree bins; TRAIN ranges 0.00614–359.99541 degrees. [Yaw evidence](evidence/full_human_yaw.json) and the full tables include validation/test histograms. Distance bands use normalized ground-footprint radius, not absolute camera distance or pixel size; upright-body foreshortening, azimuth and mixed altitudes/viewpoints prevent interpreting them as a monotonic pixel-size axis.

| Person pixel-area group | Train | Validation | Test |
| --- | --- | --- | --- |
| Very small (<64 px²) | 3,757 (24.892%) | 182 (23.916%) | 222 (28.571%) |
| Small (64–<1,024 px²) | 10,305 (68.277%) | 519 (68.200%) | 488 (62.806%) |
| Medium (1,024–<9,216 px²) | 1,031 (6.831%) | 60 (7.884%) | 67 (8.623%) |
| Large (≥9,216 px²) | 0 (0%) | 0 (0%) | 0 (0%) |

TRAIN median width / height / area at 10, 15, 20, 30, 40 m are **26 / 28 / 736**, **16 / 19 / 304**, **12 / 14 / 168**, **8 / 9 / 70**, **6 / 6 / 40** (px / px / px²). Width and height medians are summarized separately, not an actual median box. Complete count/min/p05/p25/median/p95/max/mean distributions of width, height and area are in the human JSON by split, altitude, distance and angle; readable p05/median/p95 tables are linked above. The intentional small-person coverage remains distinct from ignored boxes below 3 px. [Human balance/size figure](evidence/full_figures/human_balance_and_size.png).

Test file-list subset sizes are **all 293, single 174, multi 119, small 278, far 136, occluded 55, shadow 73**. These lists overlap and point to existing test images. All seven withheld assets occur in test and have zero train/validation use. The validator decodes and checks every image, YOLO record, metadata JSON/JSONL, completion hash, scenario and split index; all six file/index counts are 10,000. There are **10,000 unique image hashes, zero duplicate frame IDs, no split/scene/hash leakage and no orphan or corrupt exports**. The only validator warning is the known shared human template. [Full statistics](evidence/full_statistics.json) and [analysis](evidence/full_analysis.json).

## Full annotation and fidelity review

The full **300-frame audit** covers all configured altitude, angle, terrain, light and distance levels, every class, all splits, crowd bands, truncation and requested occlusion. It compares 928 matched native boxes with independent projection and freshly reproduces 929 stored object projections with **zero pixel delta**. No close/better same-class alternative appears in the spatial check; the private unique-instance simulator replay independently passes all 50 reviewed low-tail frames with identical primary box states and YOLO bytes.

| Audit class | Native boxes | Median IoU | p05 IoU | Minimum IoU |
| --- | --- | --- | --- | --- |
| person | 461 | 0.90540 | 0.41195 | 0.00554 |
| car | 152 | 0.97455 | 0.87822 | 0.49337 |
| truck | 158 | 0.98479 | 0.81576 | 0.40078 |
| bus | 157 | 0.98513 | 0.80453 | 0.36542 |
| Overall | 928 | 0.95760 | 0.53969 | 0.00554 |

Overall mean IoU is 0.89750. The distribution includes 13 `ignored_tiny` native boxes. The 915 exported labelled boxes have median 0.95818, p05 0.58716 and minimum 0.21099. The global minimum 0.00554 is a **2×4 px ignored person sliver behind a tree**, retained in metadata and not exported to YOLO. Low IoU is not an automatic annotation failure: canopy/tree/wall occlusion, cut rotated meshes at image boundaries and pixel rounding on very small people explain the reviewed tail. Requested occlusion none can still have incidental context occlusion. Native labels remain visible rectangles; no box was enlarged or hard sample discarded to raise IoU. This is a sampled cross-check, not exhaustive independent identity/visibility certification of every target.

Evidence: [300-frame audit](evidence/full_annotation_audit.json), [50 investigations](evidence/full_low_iou_investigations.json), [independent identity replay](evidence/full_instance_identity_audit.json), [IoU distribution](evidence/full_figures/annotation_iou_distribution.png), [five review pages](evidence/full_visual/low_iou_001.png) (001–005 in the same folder).

Agent visual inspection covers all **100 representative overlays**, all eight dedicated realism sheets and two native larger-human examples, including a 14-person heldout mixed scene. Human recognizability, vehicle recognizability, terrain, lighting, shadows and scene plausibility all pass the same qualitative criteria used before full generation. [Recorded review](evidence/full_realism_review.json), [human sheet](evidence/full_visual/human_focused.jpg), [single](evidence/full_visual/single_person.jpg), [multi](evidence/full_visual/multi_person.jpg), [mixed](evidence/full_visual/person_vehicle.jpg), [shadow](evidence/full_visual/shadow.jpg), [occluded](evidence/full_visual/occluded.jpg), [best](evidence/full_visual/best_quality.jpg), [weakest](evidence/full_visual/lowest_fidelity.jpg), [native 14-person test example](evidence/full_visual/native_test_007034.png). These are qualitative reviews, not calibrated realism scores.

The finite terrain/fixed far clip exposes environment background in **643/10,000 frames (6.43%)**, all at nominal 30/40 m and 30-degree off-nadir; maximum **7.045% of image pixels**. An analytical ground-ray/patch/far-plane check agrees with the reference boundary (mask IoU 0.97217). This retained difficult-factor artifact and simplified terrain/vegetation/shadows remain explicit limitations. [Extent evidence](evidence/full_background_extent_review.json).

## Performance, storage and project regression

Full generation measured **2,008.20 s (33.47 minutes), 298.775 accepted frames/minute**, 10,000 attempts and zero capture rejections. Generation timing includes startup/capture/per-frame export/shutdown and excludes aggregate rebuild, validation and QA. Full RGB occupies **4,527,294,294 bytes (4.527 GB)**, averaging 452,729 bytes per PNG. Final output totals **4,783,410,051 bytes (4.783 GB / 4.455 GiB)**, including 63,687,025 bytes of QA and 177,591,927 bytes of metadata; reused source assets elsewhere in the tooling are excluded. [Analysis](evidence/full_analysis.json).

Capture-phase Python peak RSS is **192.96 MiB**; sampled Gazebo RSS is approximately **0.81 GiB**. Aggregate rebuild/validation is a separate memory phase, with an observed Python sample of **545.0 MiB**; it is not claimed as a measured peak. Lifetime Gazebo CPU observations near 195% represent approximately two logical cores and are not instantaneous whole-host utilization. [Resource samples](evidence/full_resources.json). All capture RGB/native timestamps have zero delta; minimum settling is 0.3 s, max actual/commanded position error is 2.77e-12 m and sign-invariant quaternion error is 3.05e-11, within capture tolerances. [Owned process cleanup](evidence/full_process_cleanup.json) confirms no full-capture or private-oracle processes remain.

Final V0.4 checks **PASS**: prerequisites; all nine packages built; **56 colcon test entries with zero errors, failures or skips**; 67 baseline Python, 23 XML/SDF, 14 YAML and 24 shell files parse; all 11 launch descriptions import/generate. All nine versions remain 0.4.0. Runtime `src/`, `scripts/` and typed contracts are unchanged from frozen `v0.4-final`. All **59 synthetic unit tests** pass, including comparator sign/roundoff and meaningful-change rejection, JSON histogram/summary regressions, pose/box association, revised quotas, geometry, fidelity assets and resume/export checks. [Regression report](evidence/final_regression.json), [colcon result](evidence/final_test_results.log), [build](evidence/final_build.log), [static](evidence/final_static.json), [synthetic tests](evidence/final_synthetic_tests.log).

## Gate acceptance and reproducible commands

| Gate | Result | Actual evidence |
| --- | --- | --- |
| 0 — baseline | PASS | [PHASE0](PHASE0.md); nine-package build, 56 test entries, source release pinned |
| 1 — headless feasibility | PASS | Six native sensor channels; installed Gazebo capability evidence in PHASE0 |
| 2 — alignment and size feasibility | PASS | [Current mesh alignment](evidence/human_realism_alignment_v2/report.json), 21 cases, 448 cells, measured benchmark |
| 3 — 200-frame smoke | PASS | [Current smoke gate](evidence/smoke_gate.json), validator, 100 previews and six fidelity criteria |
| 4 — determinism | PASS | [Current 100-frame pair](evidence/human_determinism_100.json); exact RGB/YOLO/scenes with scoped metadata tolerances |
| 5 — crash/resume | PASS | [Real SIGKILL](evidence/human_crash_resume.json); 30 preserved markers, final 200 validated |
| 6 — revised 2,000-frame pilot | PASS | [Pilot gate](evidence/pilot_gate.json); quotas, distributions, visual quality, assets and performance |
| 7 — annotation cross-validation | PASS | [Audit gate](evidence/audit_gate.json); 300 frames and all 50 low-tail investigations/identity replays |
| 8 — full generation | PASS | [Evidence-based 10,000 decision](evidence/full_target_decision.json), [capture manifest](evidence/full_capture_manifest.json) |
| 9 — full validation | PASS | [Full gate](evidence/full_gate.json); automated files/hashes/splits/statistics/leakage and visual QA |
| 10 — project regression | PASS | [Final regression](evidence/final_regression.json); nine-package build, 56 baseline entries, 59 synthetic tests |

Representative actual commands (from the existing workspace, `source scripts/environment.sh`):

```bash
python3 tools/synthetic_dataset/scripts/check_determinism.py \
  datasets/human_determinism_a100 datasets/human_determinism_b100 \
  --report docs/dataset/evidence/human_determinism_100.json
python3 tools/synthetic_dataset/scripts/crash_resume_test.py \
  --output datasets/human_crash_resume \
  --report docs/dataset/evidence/human_crash_resume.json
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 10000 --seed 12345 --output datasets/gazebo_aerial_v1 --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py \
  datasets/gazebo_aerial_v1 --report docs/dataset/evidence/full_validation.json
python3 tools/synthetic_dataset/scripts/preview_dataset.py \
  datasets/gazebo_aerial_v1 --count 100 --audit-count 300
python3 docs/dataset/evidence/audit_instance_identity.py \
  datasets/gazebo_aerial_v1
python3 docs/dataset/evidence/run_final_regression.py
python3 -m unittest discover -s tools/synthetic_dataset/tests -v
```

Use a new output directory for a new run. Exact replay/resume of these captures requires **generator revision `796c48e`**, not a later documentation-only commit, plus the pinned code/config/assets/count/seed. Code SHA256 is `ea23f9a3f4e2511763931b956aa5076041623d94b23867ebd434e27a29e46a40`; full config SHA256 is `73ce8ecf411982500c61c78a86e9326b64107ea757cd30185e6913c6b0985239`; asset manifest SHA256 is `268cbd3617e529a8fb32307da9dfbba0a2b99f2d2c2905689aea421a6c36eb7a`. Bulk datasets remain gitignored; small copied reports/review artifacts have a [hash-bearing evidence snapshot](evidence/full_evidence_snapshot.json).

Failed or insufficient attempts are preserved in [continuation results](CONTINUATION_RESULTS.md): original strict quaternion comparator rejection; the fully occluded-positive crash run; low-IoU vehicle association failure; the original non-human-heavy technical pilot; inward/reflected mesh smoke; and the 50-frame replay lacking one heldout terrain source. None is presented as a pass. Corrections precede fresh affected gates; the final run uses unchanged accepted code/assets/config. The remaining milestone action is **none**: stop before training or integration.

## Use and limits

The exported `data.yaml` prepares future four-class detector use; no model was trained or evaluated here. Human evaluation subsets are overlapping file lists pointing to existing test images, never copies: all, single, multi, small, far, occluded, shadow. `small` uses documented pixel area; occluded/shadow lists use requested conditions and do not assert calibrated pixel visibility/shadow fractions. The retained VisDrone mapping is preparation only; unsupported categories remain unresolved.

**KNOWN LIMITATION:** finite static assets, shared human template, stylized vehicles/vegetation/context, planar repeated photographic materials, some finite-patch/clip image corners, hard directional shadows, simplified random layouts and very small aerial people. There is no motion/video diversity, independent unseen-human-family validation, atmospheric/terrain relief model, real-world detector score or demonstrated sim-to-real transfer. The validated result is reproducible simulator labeling/export and improved synthetic variation/fidelity. Future model work must keep heldout test scenes intact, report per-class/small-human/crowd performance, and separately evaluate real imagery.
