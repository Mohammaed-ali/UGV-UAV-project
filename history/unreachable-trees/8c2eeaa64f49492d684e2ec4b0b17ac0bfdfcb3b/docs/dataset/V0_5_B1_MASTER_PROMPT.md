# V0.5-B1 — SYNTHETIC AERIAL DETECTION DATASET GENERATOR

You are continuing the existing academic ROS 2 project:

**Wildlife Multi-UAV/UGV Simulation**

This task is a new V0.5 milestone named:

**V0.5-B1 — Synthetic Gazebo Aerial Detection Dataset Generator**

Your goal is to build a reproducible offline Gazebo Harmonic tool that generates a domain-randomized, automatically annotated aerial object-detection dataset suitable for later YOLO experiments.

You are NOT training YOLO in this task.

You are NOT modifying the current mission architecture.

You are NOT flying PX4 vehicles to collect this dataset.

The output of this milestone is a validated synthetic dataset-generation pipeline and a YOLO-format dataset.

---

# 0. SOURCE OF TRUTH

The repository is authoritative.

Before making any change:

1. Inspect the actual current repository.
2. Verify that `v0.4-final` exists.
3. Resolve its exact commit.
4. Confirm the current branch and working-tree state.
5. Read the current V0.4 documentation and source before implementing anything.

At minimum inspect:

```text
README.md
ARCHITECTURE.md
V0_4_BUILD_REPORT.md
V0_4_TEST_RESULTS.md
docs/V0_4_VALIDATION.md
docs/V0_4_CAMERA_GEOMETRY.md
docs/DEMO_GUIDE.md
```

Also inspect:

```text
wildlife_simulation
wildlife_perception
wildlife_bringup
existing Gazebo worlds
existing camera SDF/model
current camera configuration
current Gazebo set_pose usage
current validation scripts
current static checks
```

The repository wins if anything in this prompt disagrees with the actual implementation.

Do not recreate functionality that already exists.

---

# 1. RELEASE / GIT DISCIPLINE

The V0.4 release is frozen.

Start this work from:

```text
v0.4-final
```

Never modify, move, amend, retag or replace that tag.

Before branching, record:

```bash
git status
git branch --show-current
git rev-parse HEAD
git rev-parse v0.4-final^{commit}
```

Create an appropriate V0.5 development branch, for example:

```text
codex/v0.5-synthetic-dataset
```

Do not delete historical evidence or previous validation artifacts.

Commit this work in coherent checkpoints.

---

# 2. EXISTING ARCHITECTURE MUST REMAIN INTACT

Preserve the existing nine-package ROS architecture.

Do NOT:

- create another mission controller;
- create another UAV state machine;
- create another target tracker;
- create a duplicate perception architecture;
- modify frozen msg/srv/action definitions;
- alter existing operator-decision semantics;
- rewrite the PX4 adapter;
- change V0.4 mission behavior merely to support dataset generation.

The dataset generator is an **offline development tool**, not a new mission subsystem.

Prefer placing the implementation under:

```text
tools/synthetic_dataset/
```

Conceptually:

```text
tools/synthetic_dataset/
├── configs/
├── worlds/
├── models/
├── assets/
├── scripts/
├── tests/
└── README.md
```

Bulk generated datasets should go under:

```text
datasets/
```

and should be gitignored by default.

Do NOT create a tenth ROS package unless there is a compelling technical requirement.

If an existing ROS package must be changed:

1. explain why;
2. make the smallest possible change;
3. rerun the complete V0.4 regression suite.

---

# 3. PRIMARY GOAL

Build an offline synthetic dataset generator capable of producing thousands of labelled aerial images from Gazebo Harmonic.

The dataset must contain these four object-detection classes in this exact order:

```text
0 person
1 car
2 truck
3 bus
```

The generator must produce:

- RGB images;
- automatic simulator-derived ground-truth annotations;
- standard YOLO detection labels;
- train / validation / test splits;
- per-frame metadata;
- asset provenance;
- generation manifests;
- class and factor statistics;
- annotation overlays;
- QA contact sheets;
- deterministic scene generation from seeds;
- crash-safe resumable generation;
- reproducibility evidence.

Ground-truth annotations MUST come from simulator state/sensors.

Never use an object detector to generate its own training labels.

---

# 4. EXPLICITLY OUT OF SCOPE

Do NOT perform any of the following in this milestone:

- YOLO training;
- choosing the final YOLO model architecture;
- downloading VisDrone;
- VisDrone training;
- real-camera data collection;
- PX4 dataset flights;
- eight-camera fleet flight;
- ROS YOLO runtime node;
- replacing the existing OpenCV backend;
- moving-target/video dataset generation;
- wildlife/animal classes;
- tracker modifications;
- mission changes;
- UGV mechanical carrier work;
- UGV physical navigation;
- physical tray docking;
- autonomous navigation;
- sim-to-real accuracy claims.

A pretrained model inference experiment is also NOT part of the core acceptance gates.

That may be proposed later as a separate experiment.

---

# 5. DATASET GENERATION ARCHITECTURE

Do NOT fly eight PX4 vehicles to generate training data.

Do NOT require PX4.

Do NOT require QGroundControl.

Do NOT require the ROS mission graph.

Build a lightweight offline Gazebo environment containing:

```text
Gazebo dataset world
        |
        ├── movable aerial camera rig
        ├── labelled target objects
        ├── background / terrain
        ├── directional lighting
        ├── shadows
        └── optional clutter / occluders
```

Conceptually:

```text
scene sampler
     |
     +--> camera pose
     +--> targets
     +--> target orientations
     +--> materials
     +--> lighting
     +--> background
     +--> clutter
     |
     v
Gazebo
     |
     +--> RGB image
     +--> simulator ground truth
     |
     v
dataset exporter
     |
     +--> YOLO txt
     +--> metadata
     +--> manifests
     +--> QA
```

The camera may be directly teleported between poses.

It does not have to obey real UAV dynamics during dataset generation.

---

# 6. DEPENDENCY CONTROL

Keep this generator lightweight.

Preferred dependencies are:

- Python standard library;
- numpy;
- OpenCV;
- PyYAML;
- existing Gazebo / gz tooling already available to the project.

Do NOT install:

- PyTorch;
- Ultralytics;
- TensorFlow;
- large ML frameworks;

just to generate the dataset.

Do NOT add dependencies to runtime ROS packages unnecessarily.

If a new dependency becomes technically necessary:

1. state what requirement cannot be solved with existing tools;
2. state the dependency;
3. record exact version;
4. record license;
5. keep it isolated from runtime ROS components where possible.

Do not silently install new packages.

---

# 7. PHASE 0 — FEASIBILITY SPIKE

Before implementing large-scale generation, perform a dedicated feasibility phase.

Create:

```text
docs/dataset/PHASE0.md
```

Do not proceed to large-scale generation unless Phase 0 gates pass.

## 7.1 Gazebo version

Detect and record:

- Gazebo version;
- Gazebo Harmonic package versions where relevant;
- rendering engine;
- headless invocation;
- sensor/plugin availability.

Do not assume documentation for another Gazebo release applies.

---

# 8. INVESTIGATE NATIVE GAZEBO GROUND TRUTH

Test the installed system for actual support and reliability of:

- bounding-box camera;
- visible 2D boxes;
- full 2D boxes;
- 3D bounding boxes where available;
- semantic segmentation;
- instance segmentation;
- model-label systems;
- headless operation of these sensors;
- relevant gz-transport topics.

Test rather than assume.

Use this annotation preference order:

## Preferred primary method

Gazebo-native bounding-box camera producing trustworthy 2D detection boxes.

## Second preference

Instance segmentation camera followed by per-instance mask-to-tight-box conversion.

## Fallback

Projection of known oriented 3D model geometry through the actual camera model and actual simulator poses.

The fallback may also be implemented as an independent QA method.

Do NOT invent or fake unsupported Gazebo capabilities.

If a native method is unavailable or unreliable, document this clearly and use the next defensible option.

---

# 9. ANNOTATION CLASS LABELS

Avoid ambiguity between Gazebo/background label values and YOLO class IDs.

Use a separate simulator-label namespace.

For example:

```text
Gazebo label 10 -> person -> YOLO 0
Gazebo label 20 -> car    -> YOLO 1
Gazebo label 30 -> truck  -> YOLO 2
Gazebo label 40 -> bus    -> YOLO 3
```

Put the mapping in one configuration file.

Example:

```yaml
classes:
  - name: person
    gazebo_label: 10
    yolo_id: 0

  - name: car
    gazebo_label: 20
    yolo_id: 1

  - name: truck
    gazebo_label: 30
    yolo_id: 2

  - name: bus
    gazebo_label: 40
    yolo_id: 3
```

Do not scatter class mappings through source code.

---

# 10. ASSET FEASIBILITY

During Phase 0, verify suitable assets exist for all four classes:

- person;
- car;
- truck;
- bus.

Aim for several visually distinct assets per class.

Preferred target:

```text
person: >= 4 total variants where available
car:    >= 4
truck:  >= 4
bus:    >= 3
```

This target exists so at least one model can potentially be held out for testing.

If this diversity cannot be obtained from appropriate licensed assets:

- do not duplicate a mesh and pretend it is a different model;
- document the limitation;
- continue with the strongest defensible asset pool.

---

# 11. ASSET LICENSING AND PROVENANCE

Every externally obtained model, mesh, texture, terrain or material must be documented.

Prefer permissively licensed assets, such as CC0 or similarly appropriate assets where practical.

Create an asset manifest containing at least:

```text
asset_id
target/background category
model/material name
source URI
provider/author
upstream version if known
license
download date
checksum
local path
physical dimensions
train/val/test eligibility
notes
```

Pin/cache assets locally.

Later dataset generation must not silently depend on downloading mutable assets from the Internet.

Do not commit large unnecessary upstream caches if inappropriate, but preserve exact provenance.

---

# 12. VERIFY REALISTIC MODEL SCALE

Check imported target models for physically reasonable scale.

Do not assume imported Gazebo/Fuel assets use correct units.

Sanity-check approximate dimensions.

Examples only:

```text
adult person height: roughly 1.6–1.9 m
passenger car length: roughly 4–5 m
bus length: roughly 10–13 m
```

Truck dimensions depend strongly on chosen model type.

Record actual model dimensions.

Fix obviously incorrect scale.

Do not force all assets to identical dimensions.

---

# 13. FIXED CAMERA MODEL FOR DATASET V1

Reuse the current validated project down-camera as the dataset V1 camera model.

Read exact configuration from the actual current repository.

The current project camera is expected to be approximately:

```text
640 × 480
```

but verify all exact values from source.

For dataset V1, do NOT randomize:

- camera resolution;
- focal length;
- FOV;
- principal point;
- camera intrinsics.

Use the current project's actual:

- resolution;
- horizontal FOV;
- vertical FOV;
- near/far clipping;
- optical-frame convention;
- relevant noise configuration.

Record the camera model in dataset metadata.

If RGB and annotation sensors are separate sensors, ensure they use equivalent:

- pose;
- orientation;
- resolution;
- FOV;
- clipping;
- timing.

Prove they are aligned.

---

# 14. PIXEL-SIZE FEASIBILITY ANALYSIS

During Phase 0, create a pixel-size feasibility table.

For each relevant combination of:

```text
class
altitude
off-nadir angle
distance band
```

estimate or measure expected:

```text
bbox width in pixels
bbox height in pixels
bbox area
```

Required altitude buckets:

```text
10 m
20 m
30 m
40 m
```

Required off-nadir buckets:

```text
0°
10°
20°
30°
```

Also inspect existing V0.4 mission/camera profiles and identify actual operational observation/search altitudes.

If an important validated V0.4 altitude is materially different from the nominal 10/20/30/40 m set, consider adding it as an additional configured bucket.

Do not silently remove difficult factor levels.

Flag combinations where targets may fall below the configured `min_box_px`.

For problematic cells, explicitly choose one of:

- retain as a difficult sample;
- reduce sampling probability;
- restrict only that class/range combination;
- mark as ignored-small;
- revise the minimum-size threshold.

Document the decision.

---

# 15. HEADLESS PERFORMANCE BENCHMARK

Benchmark representative headless rendering before generating the pilot/full dataset.

Use:

- the fixed 640×480 camera;
- shadows enabled;
- representative object count;
- representative clutter.

Measure at least:

```text
accepted frames / minute
attempted frames / minute
CPU load
memory use
disk write rate
average image size
```

Use this to estimate generation cost.

Do not prematurely parallelize.

Start with a single generator.

---

# 16. DOMAIN RANDOMIZATION — CAMERA ALTITUDE

Required nominal altitude buckets:

```text
10 m
20 m
30 m
40 m
```

Default configurable jitter:

```text
±1 m
```

Interpret altitude as AGL relative to the local ground plane.

Record:

```text
nominal altitude bucket
actual altitude
camera world Z
ground reference
```

Coverage should be approximately balanced.

---

# 17. CAMERA VIEWING ANGLE

Interpret angle explicitly as **off-nadir angle**.

Definitions:

```text
0°  = vertically downward
10° = 10° away from nadir
20° = 20° away from nadir
30° = 30° away from nadir
```

Use nominal buckets:

```text
0
10
20
30 degrees
```

Default configurable jitter:

```text
±2°
```

Randomize viewing azimuth/camera yaw across:

```text
0° <= yaw < 360°
```

Optional small roll jitter may be used.

Record exact:

- roll;
- pitch;
- yaw;
- quaternion;
- nominal off-nadir bucket;
- actual off-nadir angle;
- viewing azimuth.

---

# 18. LIGHTING DOMAIN RANDOMIZATION

Implement four real lighting families:

```text
morning
noon
evening
shadow
```

Do not make these merely metadata labels.

Suggested initial parameter ranges:

## Morning

```text
sun elevation approximately 10–30°
warmer illumination
randomized sun azimuth
```

## Noon

```text
sun elevation approximately 60–85°
more neutral illumination
```

## Evening

```text
sun elevation approximately 3–15°
warm/orange illumination
azimuth distribution distinguishable from morning
```

## Shadow

```text
sun elevation approximately 25–55°
real shadow-casting geometry present
```

The shadow family should deliberately create some scenes where at least one target is partially in cast shadow.

Possible occluders:

- trees;
- walls;
- boxes;
- structures.

Randomize conservatively:

- sun azimuth;
- directional-light direction;
- intensity;
- color;
- ambient level;

within documented ranges.

Record actual lighting parameters per frame.

Do not claim photometric realism.

---

# 19. BACKGROUND DOMAIN RANDOMIZATION

Required families:

```text
grass
dirt
road
mixed
```

These must be visibly distinct.

For each normal background family, aim for several material/texture variants.

An ideal asset pool would support:

```text
>= 3 train-visible texture variants per family
+
>= 1 possible held-out test variant
```

If asset availability prevents this, document it.

Randomize, where technically appropriate:

- material variant;
- texture rotation;
- texture scale;
- texture offset.

The `mixed` environment should contain at least two distinguishable surface types and preferably a road strip.

Do not make all mixed scenes identical.

---

# 20. TARGET OBJECT RANDOMIZATION

Classes:

```text
person
car
truck
bus
```

Randomize:

- model variant;
- color/material where practical;
- world position;
- yaw;
- target count;
- class mixture.

Object yaw must cover:

```text
0° <= yaw < 360°
```

Prefer continuous uniform sampling or a sufficiently fine stratified distribution.

Record exact yaw per instance.

Persons may optionally receive pose/animation variation if that is reliable and does not complicate annotation.

It is not required for dataset V1.

---

# 21. OBJECT COUNT DISTRIBUTION

Do not generate only isolated one-object scenes.

Default overall frame mixture:

```text
~10% completely target-free / negative frames

~10% distractor-only frames

remaining ~80% positive target scenes
```

Positive scenes should contain approximately:

```text
1–8 target instances
```

with configurable distribution.

Include:

- single-object scenes;
- multiple same-class targets;
- mixed-class scenes;
- moderately crowded scenes.

Avoid physically impossible object interpenetration.

Use minimum footprint spacing.

---

# 22. DISTRACTORS

Distractor-only and positive scenes may include non-target objects such as:

- trees;
- rocks;
- crates;
- barriers;
- signs;
- poles;
- buildings;
- other non-target structures.

Distractors should not receive one of the four target labels.

Their purpose is to prevent an unrealistically simple world where every salient object is a target.

---

# 23. TARGET PLACEMENT

Place vehicles on plausible:

- road;
- dirt;
- flat-ground;

surfaces when appropriate.

Persons may appear on a broader set of traversable surfaces.

Avoid:

- floating targets;
- buried geometry;
- impossible overlaps;
- vehicles balanced on steep/inappropriate terrain.

Use simulator geometry/state rather than assuming spawn success.

---

# 24. DISTANCE CATEGORIES

Do NOT use fixed metric ranges that fail at different altitudes.

Determine the actual camera-ground visible footprint from:

- camera altitude;
- off-nadir orientation;
- fixed camera intrinsics/FOV;
- ground plane.

Define horizontal ground distance from the camera's nadir/reference intersection as a fraction of usable footprint radius.

Use ordinary categories:

```text
near:
0.00–0.35

medium:
0.35–0.70

far:
0.70–0.90
```

Reserve:

```text
0.90–1.00
```

for an explicit:

```text
edge / truncation challenge
```

category.

This prevents normal "far" samples from being dominated by partly off-screen objects.

Record for every object:

- distance category;
- horizontal range;
- slant range;
- normalized footprint distance.

---

# 25. OCCLUSION

Generate controlled variation including:

- no occlusion;
- mild occlusion;
- moderate occlusion;
- partial shadow;
- some image-edge truncation.

Do not make the dataset dominated by fully hidden targets.

If reliable visibility information is available, compute a visible fraction.

Possible approaches include:

- visible 2D box vs full projected box;
- segmentation-visible pixels vs expected projected area.

Do not claim an occlusion metric is accurate unless validated.

Record the method used.

---

# 26. OPTIONAL SENSOR/IMAGE RANDOMIZATION

Dataset V1 may include conservative configurable image-level variation such as:

- small exposure jitter;
- mild noise;
- modest brightness variation;
- modest contrast variation;
- slight blur;
- mild gamma variation.

Heavy augmentation is NOT the responsibility of this generator.

Do not aggressively distort synthetic frames.

Do not modify geometric image content in post-processing unless annotation transforms are updated identically.

Preserve the clean rendered image where appropriate.

---

# 27. SAMPLING STRATEGY

Do NOT generate the complete Cartesian product.

Do NOT create:

```text
altitude ×
angle ×
lighting ×
background ×
class ×
distance ×
orientation ×
model ×
color × ...
```

as a full exhaustive combination.

Use reproducible stratified/quota-based random sampling.

A Latin-hypercube approach is optional only if it offers a clear advantage without introducing unnecessary dependencies.

Quota sampling is acceptable and likely preferable.

---

# 28. DISTRIBUTION TARGETS

For the completed dataset, major frame-level factors should normally be approximately balanced.

Target approximately uniform distributions for:

- altitude;
- off-nadir angle;
- lighting family;
- background family.

Each level should ideally remain within approximately:

```text
±5 percentage points
```

of its target marginal distribution.

At object-instance level, aim for reasonable balance across:

- class;
- near/medium/far.

Orientation should be approximately uniform over:

```text
0–360°
```

Camera yaw should also be approximately uniform.

Do not sacrifice annotation quality merely to meet exact quotas.

Report any imbalance.

---

# 29. REQUIRED COVERAGE TABLES

Generate at least these cross-factor coverage tables:

```text
altitude × class
off-nadir angle × class
distance category × class
background × class
lighting × class
```

Also report frame-level marginals.

---

# 30. RANDOM SEEDS

Seeds are mandatory throughout.

There must be a master seed.

All random choices must derive deterministically from configured seeds.

Same:

```text
generator revision
config
asset set
seed
```

must reproduce identical scene specifications/manifests.

Examples of seeded choices:

- split assignment;
- scene selection;
- camera pose;
- target models;
- target poses;
- object yaw;
- lighting;
- backgrounds;
- materials;
- distractors.

Do not rely on unseeded global randomness.

---

# 31. SCENE-CHANGE STRATEGY

Investigate the most reliable Gazebo mechanism.

Possible options:

- set_pose;
- preloaded object pools;
- spawn/remove services;
- generated SDF batches;
- multiple background world variants.

Measure reliability and throughput.

Choose reliability over cleverness.

If repeated spawn/delete is unstable or slow:

- preload an object pool;
- move active objects into the scene;
- move unused objects to a staging region.

If runtime terrain-material changes are unreliable:

- use pre-generated background/world variants.

Document the chosen strategy.

---

# 32. CAPTURE INTEGRITY

Every accepted sample must correspond to the scene actually rendered.

For each scene:

1. pause or control simulation as needed;
2. apply environment changes;
3. apply target changes;
4. apply camera pose;
5. allow a configurable number of rendering/simulation frames to settle;
6. READ BACK actual target/camera state from Gazebo;
7. record the realized camera pose;
8. obtain RGB image;
9. obtain image simulation timestamp;
10. obtain annotation output;
11. obtain annotation timestamp/frame identifier if available;
12. verify image/annotation correspond to the updated scene;
13. reject stale/mismatched samples;
14. save only after integrity checks pass.

Do not treat commanded pose as ground truth when actual realized state can be queried.

---

# 33. TEMPORAL CONSISTENCY

After changing a scene, verify that captured RGB data is newer than the scene/camera modification.

Where exact sensor synchronization is available, use it.

Where it is not:

- measure timing difference;
- configure an allowable tolerance;
- reject samples outside tolerance;
- document the limitation.

Do not silently pair an old image with a new pose.

---

# 34. HEADLESS OPERATION

The generator must support headless Gazebo operation.

Use the correct invocation for the installed Gazebo version.

Do not assume one command blindly.

Verify the actual command during Phase 0.

The dataset generator should not require RViz or a desktop GUI.

GUI visualization may be used for debugging/QA only.

---

# 35. PRIMARY ANNOTATION METHOD

Use the strongest simulator-native method validated in Phase 0.

Preferred order:

```text
1. Gazebo bounding-box camera

2. instance segmentation -> tight visible boxes

3. calibrated geometry projection
```

Document precisely what the selected primary method means.

For example distinguish:

- visible 2D box;
- full 2D box;
- projected full-object geometry.

Do not mix these definitions silently.

---

# 36. INDEPENDENT ANNOTATION CROSS-CHECK

Implement an independent secondary annotation calculation wherever practical.

For example:

If primary is:

```text
native bounding-box camera
```

secondary could be:

```text
instance segmentation -> tight box
```

or:

```text
3D geometry projection
```

If primary is segmentation-derived, use geometry projection as secondary.

Audit at least:

```text
300 frames
```

from pilot/full generation.

Those frames must cover:

- all four classes;
- all altitudes;
- all angle buckets;
- all lighting families;
- all background families;
- near/medium/far;
- occlusion;
- truncation.

---

# 37. ANNOTATION IOU AUDIT

For matched instances, calculate IoU between primary and secondary boxes.

Report:

- mean IoU;
- median IoU;
- 5th percentile;
- 25th percentile;
- class distribution;
- altitude distribution;
- angle distribution where useful.

Use approximately:

```text
median IoU >= ~0.90
```

as a quality goal, not an unconditional semantic truth.

If:

```text
5th percentile < ~0.75
```

investigate manually.

Classify disagreement causes such as:

- true misalignment;
- sensor timing mismatch;
- occlusion;
- truncation;
- different box semantics;
- imperfect 3D projection;
- segmentation artifacts.

Do NOT manipulate correct ground truth merely to hit an arbitrary IoU number.

---

# 38. YOLO LABEL FORMAT

Export standard YOLO detection labels:

```text
<class_id> <x_center> <y_center> <width> <height>
```

All coordinates normalized to:

```text
0.0–1.0
```

Required validation:

```text
0 <= x_center <= 1
0 <= y_center <= 1
0 < width <= 1
0 < height <= 1
```

Target class order:

```text
0 person
1 car
2 truck
3 bus
```

Every image must have a corresponding label file.

A negative/distractor-only frame must have an empty label file.

---

# 39. EDGE CLIPPING

Boxes that cross image boundaries must be clipped correctly.

Do not export invalid coordinates.

Record whether an object was truncated.

---

# 40. TINY / IGNORED OBJECT POLICY

Far/small objects are important in aerial imagery.

Do not aggressively discard them.

Provide configurable thresholds such as:

```text
min_box_px
min_box_area_px
```

A possible starting value may be roughly:

```text
minimum side ~= 3 pixels
```

but Phase 0 must evaluate this.

Every rendered target object must appear in metadata even if it is not exported as a YOLO label.

Allowed states should include at least:

```text
labelled
ignored_tiny
ignored_outside
ignored_occluded
ignored_invalid
ignored_other
```

Store the reason.

Never leave a clearly visible target absent from both label files and metadata.

---

# 41. VISIBLE-FRACTION POLICY

If a reliable visible fraction can be computed, store it.

A starting experimental rule such as:

```text
visible fraction >= 0.4
```

may be evaluated.

Do NOT make `0.4` an unquestioned universal rule before Phase 0 validates what the metric actually measures.

Keep the threshold configurable.

---

# 42. DATASET DIRECTORY STRUCTURE

Create a structure similar to:

```text
datasets/
└── gazebo_aerial_v1/
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    │
    ├── labels/
    │   ├── train/
    │   ├── val/
    │   └── test/
    │
    ├── metadata/
    │   ├── train.jsonl
    │   ├── val.jsonl
    │   └── test.jsonl
    │
    ├── manifests/
    │   ├── assets.csv
    │   ├── scenarios.csv
    │   ├── generation_config.yaml
    │   └── class_mapping.yaml
    │
    ├── qa/
    │   ├── previews/
    │   ├── contact_sheets/
    │   ├── low_iou/
    │   └── statistics/
    │
    ├── data.yaml
    ├── manifest.json
    ├── statistics.json
    └── README.md
```

Bulk images/labels should not be committed to the main source repository by default.

---

# 43. DATA.YAML

Generate a standard YOLO dataset file:

```yaml
path: /path/to/gazebo_aerial_v1

train: images/train
val: images/val
test: images/test

names:
  0: person
  1: car
  2: truck
  3: bus
```

Do not install Ultralytics merely to create this file.

---

# 44. PER-FRAME METADATA

Create machine-readable metadata, preferably JSONL.

For every frame record at least:

## Identity

```text
frame ID
split
scene ID
master seed
scene seed
simulation timestamp
generation timestamp
```

## Camera

```text
camera model
actual realized world position
actual realized orientation
roll/pitch/yaw
quaternion
altitude AGL
nominal altitude bucket
actual off-nadir angle
off-nadir bucket
viewing azimuth
resolution
FOV
intrinsics
near/far clipping
```

## Environment

```text
background family
background material/asset
lighting family
actual light direction
sun/light elevation
sun/light azimuth
intensity
color/temperature description where applicable
shadow configuration
```

## Each target object

```text
instance ID
class
YOLO class ID
Gazebo label
asset/model name
actual world pose
actual yaw
physical dimensions
horizontal camera range
slant range
distance category
pixel bbox
normalized bbox
visible fraction if available
occlusion status
truncation status
label state
ignored reason if applicable
```

Also record distractor identities if practical.

---

# 45. DATASET PROVENANCE MANIFEST

Generate:

```text
manifest.json
```

containing at least:

```text
dataset name
dataset version
source project release
source release commit
generator Git commit
Gazebo version
generation configuration hash
camera configuration hash
class mapping
master random seed
asset manifest reference
asset licenses
dataset-generation start/end times
attempted samples
accepted samples
rejected samples
rejection reasons
split counts
class counts
factor distributions
host/runtime information where useful
```

Create SHA-256 hashes for:

- critical configuration files;
- manifests;
- asset manifest;
- deterministic file index;

and generated files where practical without making the process unreasonably expensive.

---

# 46. TRAIN / VAL / TEST SPLITTING

Do NOT split random adjacent frames from the same scene family across train and test.

Split by:

```text
scene / seed family
```

The three splits must be disjoint.

Default full-dataset target split:

```text
80% train
10% validation
10% test
```

This is configuration-controlled.

---

# 47. HELD-OUT TEST ASSETS

Where the available asset pool permits, make the test set more challenging by holding out:

```text
>= 1 model variant per class
>= 1 texture/material variant per background family
```

from train/validation.

These held-out assets appear only in test.

Do not fabricate held-out model diversity by recoloring one identical mesh and calling it a different model.

If asset scarcity prevents a held-out asset for a category:

- record it;
- do not pretend the requirement was met.

---

# 48. SPLIT LEAKAGE TESTS

Check for:

- duplicate frame IDs;
- duplicate file hashes;
- repeated identical scenario IDs;
- scene-family overlap;
- held-out-asset leakage;
- identical pose/configuration replay where not intended.

Report all leakage checks.

---

# 49. STAGED GENERATION

Do NOT immediately generate the full dataset.

Use three stages.

## Stage A — Smoke dataset

Generate approximately:

```text
200 accepted frames
```

Purpose:

- prove RGB capture;
- prove automatic labels;
- verify class mapping;
- test metadata;
- test YOLO export;
- test negative frames;
- test reproducibility;
- test validator;
- visual inspection.

Do not proceed if this fails.

## Stage B — Pilot dataset

Generate approximately:

```text
2,000 accepted frames
```

Purpose:

- assess distribution balance;
- test annotation quality;
- run 300-frame annotation cross-check;
- benchmark throughput;
- assess storage;
- inspect small-object distribution;
- test split isolation;
- test held-out assets;
- refine only justified parameters.

## Stage C — Full dataset

Default planning target:

```text
10,000 accepted frames
```

Default split:

```text
8,000 train
1,000 validation
1,000 test
```

This target may be adjusted only after Phase 0 and pilot evidence.

If measured throughput/storage/quality strongly justifies another final count, report:

- proposed final count;
- reason;
- estimated generation time;
- storage requirement;

before silently changing the target.

A full dataset smaller than approximately 2,000 frames must not be described as a full dataset; it is a pilot.

---

# 50. CAPTURE ONE INTENTIONAL SCENE PER SAMPLE

Avoid saving consecutive near-identical video frames.

Normally:

```text
one explicitly configured scene
=
one accepted sample
```

unless a deliberately documented temporal variation experiment is later added.

This milestone is still-image object detection, not video learning.

---

# 51. RESUMABLE GENERATION

Generation must survive interruption.

Use stable deterministic frame/sample IDs.

For example:

```text
scene_<scene_seed>_<sample_index>
```

Do not overwrite valid completed frames accidentally.

Use atomic file-writing behavior where appropriate:

1. write temporary file;
2. close/flush;
3. rename to final path after success.

Consider a frame complete only after:

- RGB image exists;
- YOLO label exists;
- metadata exists;
- sample status is committed.

On restart:

- detect valid completed samples;
- skip them;
- detect incomplete/corrupt samples;
- regenerate only what is necessary.

---

# 52. CRASH / RESUME ACCEPTANCE TEST

During smoke/pilot validation:

1. start a generation run;
2. deliberately terminate it mid-run;
3. restart with `--resume`.

PASS only if:

- final expected count is correct;
- no duplicate frame IDs;
- no duplicate manifest entries;
- no corrupt partial files;
- image/label/metadata counts agree.

---

# 53. COMMAND-LINE INTERFACE

Provide one clear primary command.

Conceptually:

```bash
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 200 \
  --seed 12345 \
  --output datasets/gazebo_aerial_v1 \
  --headless
```

Required options:

```text
--config
--count
--seed
--output
--headless
--resume
```

Optional useful arguments may include:

```text
--split
--preview
--validate-only
```

Do not overcomplicate version 1.

---

# 54. SINGLE AUTHORITATIVE CONFIG FILE

Experiment parameters must be configurable without editing Python.

Use one primary YAML configuration with optional referenced class/asset configs.

Configurable values must include:

```text
master seed
dataset size
split fractions
altitude buckets
altitude jitter
off-nadir buckets
angle jitter
camera yaw distribution
lighting ranges
background families
asset pools
object-count distribution
negative-frame ratio
distractor-only ratio
distance bands
occlusion options
minimum spacing
min_box_px
minimum bbox area
visibility threshold if used
settling frames
sync/timestamp tolerance
output location
```

Do not scatter experiment constants through scripts.

---

# 55. DATASET VALIDATOR

Create a standalone validator.

It must check every split.

At minimum:

```text
every image has a label file
every image has metadata
every metadata record has expected image/label
all images decode successfully
no zero-byte files
all YOLO classes valid
all normalized bbox values valid
all boxes have positive width/height
all clipped boxes lie inside image
no NaN/Inf metadata
negative frames have empty label files
no duplicate frame IDs
no duplicate images by hash where prohibited
no scene overlap between splits
held-out assets do not leak into train
all four classes represented
all altitude buckets represented
all angle buckets represented
all lighting families represented
all background families represented
near/medium/far represented
```

Also verify expected counts agree across:

- images;
- labels;
- metadata;
- manifest.

---

# 56. DATASET STATISTICS

Produce at least:

```text
frames per split
positive frames
negative frames
distractor-only frames
object instances per class
objects per image
instances by altitude
instances by off-nadir angle
instances by lighting
instances by background
instances by distance category
object yaw histogram
camera yaw histogram
bbox width distribution
bbox height distribution
bbox area distribution
small/medium/large-object distribution
ignored-object counts by reason
truncated-object count
occlusion statistics if available
```

Also produce required cross tables.

---

# 57. VISUAL QA

Create annotation-preview tools.

Render overlays containing:

- class name;
- bounding box;
- optional instance ID;
- optional range;
- useful scene metadata.

Create at least:

```text
100 representative random annotated previews
```

covering all major factors.

Also produce dedicated contact sheets for:

- each class;
- each altitude;
- each angle;
- each lighting family;
- each background;
- near;
- medium;
- far;
- edge/truncation;
- shadows;
- occlusion;
- multi-object scenes;
- negative frames;
- distractor-only frames.

Visual inspection is a formal acceptance step.

---

# 58. LOW-IOU QA

From the 300-frame annotation cross-check:

identify lowest-agreement cases.

Create a contact sheet containing approximately:

```text
50 lowest-IoU audited samples
```

Include:

- primary annotation;
- secondary annotation;
- class;
- altitude;
- scene information;
- IoU.

Use these to distinguish actual bugs from legitimate box-definition differences.

---

# 59. CONTROLLED ALIGNMENT TEST WORLD

Create a deterministic alignment test.

Place known instances of:

```text
person
car
truck
bus
```

at controlled world positions.

Test at minimum:

- centered;
- near image edge;
- partially truncated;
- partially occluded;
- near;
- far;
- multiple objects.

Verify:

```text
RGB object
Gazebo/model label
ground-truth annotation
YOLO export
```

all correspond.

Do not declare the annotation system correct merely because files exist.

---

# 60. DETERMINISM TEST

Generate a small deterministic sequence twice.

Example:

```text
Run A: 50 scenes, seed 12345
Run B: same Git revision/config/assets/seed
```

Compare:

- frame IDs;
- scene IDs;
- model selection;
- target positions;
- target orientations;
- camera poses;
- lighting parameters;
- backgrounds;
- label coordinates;
- metadata;
- scenario manifest.

These should reproduce.

If rendered RGB bytes also reproduce, report that.

If renderer behavior produces non-identical RGB hashes despite identical scene specifications:

- do not hide it;
- record the limitation;
- require scene/label/metadata determinism instead.

---

# 61. DATASET FILE HASHES

For reproducibility, maintain a deterministic file index.

Use SHA-256 as appropriate.

Do not create a huge expensive hashing system that prevents practical generation, but ensure critical metadata/configuration/artifacts are verifiable.

---

# 62. VISDRONE FUTURE-MAPPING CONFIG

Create:

```text
tools/synthetic_dataset/configs/visdrone_class_map.yaml
```

This is preparation only.

Do NOT download VisDrone.

Suggested mapping:

```yaml
project_classes:
  0: person
  1: car
  2: truck
  3: bus

visdrone_mapping:
  pedestrian: person
  people: person
  car: car
  truck: truck
  bus: bus
```

Do NOT silently map these classes yet:

```text
van
bicycle
motor
tricycle
awning-tricycle
```

Their treatment belongs to the later YOLO-training milestone.

---

# 63. DO NOT CLAIM PHOTOREALISM

Documentation must explicitly state:

```text
Synthetic Gazebo imagery is not equivalent to real aerial-camera imagery.
```

This dataset provides:

- domain randomization;
- controlled geometry;
- perfect simulator metadata;
- scalable labels.

It does NOT establish:

- real-world detector accuracy;
- real UAV camera performance;
- VisDrone-equivalent visual realism;
- sim-to-real success.

The later experiment will test whether synthetic data improves generalization.

Do not claim the answer before measuring it.

---

# 64. TESTS FOR GENERATOR CODE

Add focused automated tests.

At minimum:

1. class mapping;
2. Gazebo-label -> YOLO-class conversion;
3. pixel bbox -> normalized YOLO conversion;
4. clipping;
5. invalid bbox rejection;
6. ignored-object metadata;
7. negative-frame handling;
8. split assignment;
9. scene split isolation;
10. held-out asset enforcement;
11. reproducible random sampling;
12. altitude bucket selection;
13. off-nadir bucket selection;
14. yaw range;
15. distance-category calculation;
16. footprint geometry;
17. metadata serialization;
18. manifest generation;
19. dataset YAML generation;
20. image/label/metadata matching;
21. duplicate detection;
22. resume logic.

Where practical, geometry logic should be testable without launching full Gazebo.

---

# 65. V0.4 REGRESSION

Before changes, run or inspect the appropriate baseline validation.

After implementation, rerun the full existing automated V0.4 build/test suite.

At minimum, use the repository's established commands, expected approximately to include:

```bash
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh

colcon test --base-paths src --executor sequential
colcon test-result --verbose
```

Use the actual repository scripts if names/options differ.

The established baseline is expected to be:

```text
9 packages
56 colcon entries
0 errors
0 failures
0 skipped
```

Do not merely assume this; verify.

Run existing static checks as well.

If dataset tooling lives fully outside ROS packages, that is still not permission to skip regression.

---

# 66. DO NOT AFFECT EXISTING DEMOS

Existing V0.4 demos must remain independently usable.

The synthetic dataset assets/tooling must not become required dependencies for:

- logic-only demo;
- single-PX4 demo;
- camera mission;
- two-camera mission;
- fleet validation.

Do not make ordinary mission launch depend on a large synthetic-data asset pool.

---

# 67. DOCUMENTATION

Create:

```text
docs/dataset/PHASE0.md
docs/dataset/DATASET_REPORT.md
```

Also create appropriate tooling README documentation.

`DATASET_REPORT.md` must explain:

- architecture;
- source baseline;
- Gazebo version;
- annotation method;
- why that method was chosen;
- camera model;
- target classes;
- asset sources/licenses;
- physical-scale verification;
- scene randomization;
- sampling strategy;
- dataset split strategy;
- held-out test assets;
- metadata;
- synchronization;
- reproducibility;
- annotation QA;
- IoU cross-check;
- dataset statistics;
- performance;
- known limitations;
- sim-to-real domain gap;
- future YOLO use.

---

# 68. USE EXISTING PROJECT REPORTING VOCABULARY

Use these exact concepts where appropriate:

```text
PASSED
PARTIALLY VALIDATED
NOT TESTED
KNOWN LIMITATION
```

Do not convert partial evidence into a PASS.

Keep failed attempts and diagnostic evidence where useful.

---

# 69. REQUIRED EVIDENCE

At completion, preserve evidence for:

- Phase-0 feasibility;
- asset/license manifest;
- camera configuration;
- pixel-size feasibility table;
- alignment test;
- smoke dataset;
- pilot dataset;
- full dataset summary;
- distribution statistics;
- annotation cross-check;
- low-IoU examples;
- contact sheets;
- determinism run;
- resume/crash test;
- validator output;
- final V0.4 regression.

Do not commit the entire multi-GB dataset to Git unless explicitly required.

Commit small representative QA images if appropriate.

---

# 70. DEVELOPMENT ORDER

Follow this exact sequence.

## Gate 0 — Baseline

Confirm:

- `v0.4-final`;
- repository clean/source state;
- baseline build/tests.

Report before modifying source.

## Gate 1 — Phase 0

Verify:

- Gazebo version;
- native annotation capabilities;
- headless operation;
- four target classes/assets;
- physical scale;
- camera configuration;
- headless throughput;
- pixel-size feasibility.

PASS only if at least one reliable annotation method exists and all four classes are feasible.

## Gate 2 — Ground-truth proof of concept

Use one controlled example per class.

Verify RGB/annotation alignment.

PASS only after visual and programmatic confirmation.

## Gate 3 — Smoke dataset

Generate approximately:

```text
200 accepted frames
```

Run full validator and manual QA.

## Gate 4 — Determinism

Generate the same small scenario set twice with identical seed/config.

Compare manifests.

## Gate 5 — Resume/crash

Interrupt generation and successfully resume it without duplicates/corruption.

## Gate 6 — Pilot dataset

Generate approximately:

```text
2,000 accepted frames
```

Analyze:

- balance;
- object size;
- annotation quality;
- asset diversity;
- disk usage;
- throughput.

## Gate 7 — Annotation cross-validation

Audit at least:

```text
300 frames
```

using independent primary/secondary box methods.

Produce IoU analysis and lowest-IoU QA.

## Gate 8 — Full dataset

Default target:

```text
10,000 accepted frames
```

unless Phase 0/pilot evidence justifies a documented revision.

## Gate 9 — Full dataset validator

Require:

- zero invalid YOLO coordinates;
- zero corrupted images;
- matching image/label/metadata counts;
- no scene split leakage;
- required class/factor representation;
- held-out test asset policy satisfied where feasible.

## Gate 10 — V0.4 regression

Run complete existing build/test/static regression.

The new dataset tool must not regress the project.

---

# 71. FULL-DATASET ACCEPTANCE CRITERIA

This milestone is DONE only when all applicable criteria below are satisfied.

1. The generator runs headlessly.

2. It uses the existing fixed V0.4 camera model for dataset V1.

3. All four classes are represented:

```text
person
car
truck
bus
```

4. Simulator-derived annotations work.

5. RGB and annotation streams are demonstrated to correspond.

6. Altitude covers:

```text
10
20
30
40 m
```

plus any intentionally added project-specific altitude.

7. Off-nadir covers:

```text
0
10
20
30 degrees
```

8. Camera yaw covers:

```text
0–360°
```

9. Object yaw covers:

```text
0–360°
```

10. Lighting includes:

```text
morning
noon
evening
shadow
```

11. Background includes:

```text
grass
dirt
road
mixed
```

12. Distance includes:

```text
near
medium
far
```

with edge/truncation represented separately.

13. Multi-object scenes exist.

14. Negative scenes exist.

15. Distractor-only scenes exist.

16. Shadow/occlusion examples exist.

17. YOLO labels are valid.

18. Every rendered target is accounted for in labels or ignored-object metadata.

19. Train/val/test are disjoint by scene.

20. Held-out test assets are used where the asset pool permits.

21. Same seed/config reproduces the scene manifest.

22. Crash/resume works.

23. QA contact sheets exist.

24. Independent annotation cross-check exists.

25. Distribution statistics exist.

26. Provenance/asset licenses are recorded.

27. Smoke and pilot datasets pass QA before full generation.

28. Full dataset validator passes.

29. Existing V0.4 regression still passes.

30. Documentation clearly states that this synthetic dataset does NOT prove real-world accuracy.

---

# 72. REPORTING FORMAT TO THE USER

Work incrementally.

For every gate report:

1. What you inspected.
2. What actually exists.
3. What you attempted.
4. What method you selected.
5. Why.
6. Files created/modified.
7. Commands run.
8. PASS / FAIL.
9. Evidence.
10. Warnings.
11. Known limitations.
12. Next gate.

Do not hide failed attempts.

Do not claim PASS without evidence.

If the repository contradicts this prompt:

**THE REPOSITORY WINS.**

If the installed Gazebo version lacks an assumed feature:

**DO NOT FAKE IT.**

Use the strongest reliable supported alternative and document the limitation.

---

# 73. FINAL DELIVERABLES

Expected source/tooling deliverables:

```text
tools/synthetic_dataset/
    configs/
    worlds/
    models/
    assets/manifests/
    scripts/
    tests/
    README.md
```

Expected configuration includes:

```text
synthetic_dataset.yaml
class_mapping.yaml
visdrone_class_map.yaml
```

Expected scripts include equivalents of:

```text
generate_dataset.py
validate_dataset.py
preview_dataset.py
```

plus shell wrappers only if consistent with project style.

Expected documentation:

```text
docs/dataset/PHASE0.md
docs/dataset/DATASET_REPORT.md
```

Expected dataset output:

```text
datasets/gazebo_aerial_v1/
```

with:

```text
images
labels
metadata
manifests
qa
data.yaml
manifest.json
statistics.json
README.md
```

---

# 74. STOP CONDITION

When the synthetic dataset generator has passed all applicable gates and the V0.4 regression remains clean:

STOP.

Do NOT begin:

- YOLO installation;
- YOLO training;
- VisDrone download;
- VisDrone conversion;
- model comparison;
- ROS YOLO node integration.

Those belong to the NEXT milestone.

The likely later experiment will compare:

```text
A. generic pretrained YOLO

B. YOLO fine-tuned on VisDrone

C. YOLO fine-tuned on Gazebo synthetic data

D. YOLO fine-tuned on VisDrone + Gazebo synthetic data
```

using fixed held-out evaluation datasets.

That future experiment is deliberately separate from V0.5-B1.

END OF TASK.