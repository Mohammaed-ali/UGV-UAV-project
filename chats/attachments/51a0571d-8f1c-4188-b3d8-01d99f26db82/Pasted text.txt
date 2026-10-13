# HUMAN-FOCUSED DATASET SAMPLING REQUIREMENT

The project now has an explicit priority:

**Improve future YOLO detection performance for humans/persons.**

Modify the synthetic-dataset sampling strategy accordingly.

Do NOT simply duplicate existing human images.

Generate genuinely different human scenes with variation in:

- position;
- altitude;
- camera angle;
- distance;
- orientation;
- human model/appearance;
- lighting;
- terrain;
- shadows;
- occlusion;
- crowd size;
- image-edge placement.

The YOLO class definition remains:

```text
0 person
1 car
2 truck
3 bus
```

---

## 1. HUMAN-HEAVY TRAINING SPLIT

Make the TRAINING split deliberately human-heavy.

Target approximately:

```text
60% of all training images:
contain at least one person

20%:
contain vehicles but no person

10%:
distractor-only

10%:
completely target-free / negative
```

This means approximately 75% of positive training scenes should contain humans.

These percentages must remain configurable in YAML.

Do NOT apply the same human oversampling blindly to validation and test.

Validation/test should remain closer to the intended evaluation distribution so model performance can be measured honestly.

---

## 2. SINGLE-HUMAN VS MULTI-HUMAN SCENES

Within training images containing humans, deliberately generate both isolated humans and groups.

Target approximately:

```text
45% of human-containing frames:
exactly 1 visible person

55% of human-containing frames:
2 or more visible persons
```

For the multi-human portion, aim approximately for:

```text
40%:
2–3 persons

35%:
4–6 persons

20%:
7–10 persons

5%:
11+ persons
```

Treat these as configurable targets rather than rigid mathematical requirements.

Do not create physically impossible crowds or excessive overlap.

---

## 3. IMPORTANT: INSTANCE BALANCE

Because multi-human scenes contain many person instances, monitor BOTH:

```text
percentage of frames containing humans
```

and:

```text
total number of person bounding boxes
```

Do not allow crowd scenes alone to create nearly all person instances.

Report:

```text
person frames
single-person frames
multi-person frames

person instances total

instances in:
1-person scenes
2–3-person scenes
4–6-person scenes
7–10-person scenes
11+-person scenes
```

---

## 4. HUMAN DISTANCE COVERAGE

Humans are usually smaller than vehicles in aerial imagery.

Therefore make human sampling explicitly cover:

```text
near
medium
far
edge/truncation
```

Aim for approximately balanced human-instance coverage across:

```text
near
medium
far
```

while maintaining a smaller intentional edge/truncation subset.

Do not concentrate humans only near the camera simply because they are easier to annotate.

The purpose is to teach the future detector to recognize small aerial-view people.

---

## 5. HUMAN ALTITUDE COVERAGE

Generate humans at every configured camera altitude.

Current primary altitude buckets include:

```text
10 m
15 m
20 m
30 m
40 m
```

if 15 m remains part of the implemented configuration.

Report human-instance coverage for:

```text
altitude × person
```

Do not allow nearly all human samples to come from 10–15 m.

Higher-altitude human samples are important even if they are harder.

If a person becomes too small for a valid label, preserve the scene/object in metadata with the configured ignored-object reason.

Do not silently convert difficult human examples into missing labels.

---

## 6. HUMAN VIEWING-ANGLE COVERAGE

Humans must appear under all configured aerial viewpoints:

```text
0° off nadir
10°
20°
30°
```

and across random viewing azimuths.

Report:

```text
off-nadir angle × person instances
```

Avoid a dataset where humans are overwhelmingly photographed straight down.

---

## 7. HUMAN ORIENTATION

For standing/static person models, vary yaw across the full:

```text
0–360°
```

Do not always place people facing the same direction.

Where model support permits, include several visually distinct poses/appearances.

Do not introduce unreliable animations merely to increase variety.

---

## 8. HUMAN APPEARANCE DIVERSITY

Prioritize visual diversity for the person class.

Where technically and legally possible, vary:

- person model;
- clothing/material colors;
- body proportions within realistic model variation;
- pose/model geometry;
- orientation.

Do not claim multiple independent human models where several variants actually share the same underlying template.

Record this honestly in the asset manifest.

If the current human asset pool is too visually repetitive, improving human asset diversity should take priority over generating substantially more near-identical frames.

---

## 9. SINGLE-PERSON SCENES

Single-person scenes are required.

They should include combinations such as:

```text
isolated person on grass
isolated person on dirt
person beside road
person on road edge
person near vehicle
person in partial shadow
person near vegetation
person partly occluded
small distant person
person near image edge
```

Do not make single-person scenes uniformly clean or centered.

---

## 10. MULTI-PERSON SCENES

Generate deliberate multi-person configurations.

Examples:

```text
two people separated widely

two people close together

small group of 3

group of 4–6

larger group

people around a vehicle

people along a road

people on mixed terrain

partially occluded group

some people in shadow and some illuminated

different distances from camera within one image
```

Do not place every person at the same orientation or exact spacing.

---

## 11. HUMAN + VEHICLE MIXED SCENES

Include significant numbers of scenes containing both:

```text
person + car
person + truck
person + bus
multiple people + vehicle
multiple people + multiple vehicles
```

This is important so the future model does not learn that:

```text
human scene = no vehicles
```

or:

```text
vehicle scene = no humans
```

Scene composition must not create artificial class correlations.

---

## 12. OCCLUSION

Human detection must include realistic partial occlusion.

Generate examples where a person is partly obscured by:

```text
another person
car
truck
bus
tree
wall
pole
crate
other scene geometry
```

Use mild/moderate occlusion more frequently than severe occlusion.

Avoid a training set dominated by humans that are nearly invisible.

Record visibility/occlusion information where available.

---

## 13. SHADOW CONDITIONS

Ensure humans occur under all lighting families:

```text
morning
noon
evening
shadow
```

For the shadow category, deliberately include:

```text
person completely illuminated

person partly in cast shadow

group containing mixed illuminated/shadowed people
```

Do not make "shadow" mean simply lowering global image brightness.

---

## 14. BACKGROUND COVERAGE

Humans must appear across:

```text
grass
dirt
road
mixed
```

Do not make person detections overwhelmingly associated with one background.

Report:

```text
background × person instances
```

---

## 15. HUMAN PIXEL-SIZE STATISTICS

Create human-specific bounding-box statistics.

Report:

```text
person bbox width
person bbox height
person bbox area
```

with distributions by:

```text
altitude
distance
off-nadir angle
```

Explicitly report percentages of person instances that are:

```text
very small
small
medium
large
```

Use pixel-area thresholds defined/documented by the project.

This is particularly important because the future detector's aerial-human performance depends heavily on small-object representation.

---

## 16. DO NOT ACHIEVE HUMAN EMPHASIS BY DUPLICATION

Do NOT simply copy an existing person image multiple times.

Do NOT count trivial recoloring of the exact same frame as additional scene diversity.

Human emphasis must primarily come from newly generated scene states.

Different samples should vary meaningful factors such as:

```text
camera pose
person position
person orientation
person model
distance
lighting
background
crowd composition
occlusion
other nearby objects
```

---

## 17. TRAINING VS VALIDATION/TEST

Human oversampling should primarily affect TRAINING.

Keep validation and test suitable for unbiased comparison.

For the normal validation/test splits, maintain useful representation of:

```text
person
car
truck
bus
negative scenes
distractors
mixed scenes
```

Additionally create human-focused evaluation metadata/subsets WITHOUT duplicating files, for example:

```text
test_person_all
test_person_single
test_person_multi
test_person_small
test_person_far
test_person_occluded
test_person_shadow
```

These may be represented through manifests/file lists rather than copying images.

This allows future evaluation of human-specific performance.

---

## 18. SAMPLER IMPLEMENTATION

Do not rely on pure random sampling to happen to produce enough human scenes.

Implement explicit configurable quotas.

The dataset config should include something conceptually like:

```yaml
class_priority:
  person:
    enabled: true

training_scene_composition:
  human_positive_fraction: 0.60
  vehicle_only_fraction: 0.20
  distractor_only_fraction: 0.10
  empty_fraction: 0.10

human_scene_distribution:
  single_person_fraction: 0.45
  multi_person_fraction: 0.55

multi_person_count_distribution:
  2_3: 0.40
  4_6: 0.35
  7_10: 0.20
  11_plus: 0.05
```

Exact config syntax may follow the implementation's existing style.

Do not create a second conflicting configuration system.

---

## 19. PILOT-DATASET REVIEW

Before full generation, use the ~2,000-frame pilot to verify whether the human emphasis actually occurred.

Report at minimum:

```text
total training images
training images containing persons
percentage containing persons

single-person images
multi-person images

total person instances

person instances by:
altitude
distance
angle
background
lighting
model
pixel-size group
occlusion level
```

Also report vehicle counts to prove that human emphasis did not accidentally remove useful vehicle coverage.

If the quotas are materially wrong, correct the SAMPLER before generating the full dataset.

Do not repair imbalance afterward by simply duplicating frames.

---

## 20. FULL-DATASET ACCEPTANCE ADDITION

Add the following acceptance criteria for the full dataset:

1. Approximately 60% of TRAIN images contain at least one person, subject to the configured tolerance.

2. Both single-person and multi-person scenes are well represented.

3. Every altitude contains valid person examples where geometrically feasible.

4. Every off-nadir angle contains person examples.

5. Every background family contains person examples.

6. Every lighting family contains person examples.

7. Near, medium and far person examples are present.

8. Small aerial-view person boxes are intentionally represented.

9. Human + vehicle mixed scenes are present.

10. Occluded and shadowed human examples are present.

11. Human asset/model diversity is reported honestly.

12. Validation/test distributions are not blindly copied from the human-heavy training distribution.

13. No human-priority target is achieved simply by duplicating existing frames.

14. Human-specific QA/statistics and evaluation subsets are produced.

The purpose of this change is to give the later YOLO training stage substantially more varied examples of the `person` class, especially isolated people, groups of people, small aerial-view people, partially occluded people, and people appearing alongside vehicles.