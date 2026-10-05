# HUMAN-FOCUSED AND HIGHER-REALISM DATASET ADDENDUM

The dataset must continue to prioritize better future detection of the `person` class, but it must also improve the **visual realism / fidelity** of the synthetic images.

Current sample outputs appear too simplified / toy-like / low-detail.

The goal is **not** to claim photorealism, but to move from very abstract synthetic scenes toward **more realistic-looking aerial imagery** that is better suited for later detector training.

Do NOT solve this by postprocessing the final exported images only.

Prefer improving the underlying scene, materials, assets, lighting and rendering configuration.

---

## 1. OVERALL VISUAL FIDELITY REQUIREMENT

Improve the dataset's visual realism while remaining within the project's synthetic-data scope.

The generated images should look less like:

```text id="2kz3ev"
simple toy scene
flat-color geometric blocks
repetitive low-detail textures
overly clean synthetic layout
```

and more like:

```text id="q2tnwp"
simplified but credible aerial-view outdoor imagery
recognizable people
recognizable road vehicles
more natural terrain/material variation
more believable lighting and shadow
better object/ground interaction
more realistic scene clutter
```

This is a **visual-fidelity improvement goal**, not a claim of real-world photorealism.

Document clearly that the resulting data is still synthetic.

---

## 2. PRIORITY ORDER

When improving realism, use this priority order:

### Highest priority
1. **human visual quality**
2. **vehicle visual quality**
3. **terrain/background realism**
4. **lighting / shadows**
5. **scene clutter and context**
6. **render quality / anti-aliasing**

Do not spend large effort on cosmetic effects while the people still look like crude markers.

---

## 3. HUMAN VISUAL QUALITY IMPROVEMENT

The person class is a priority class and must become visually more realistic.

Improve person assets so that humans are more clearly human-shaped from aerial views.

Prefer assets with:

- recognizable head / torso / limb proportions;
- more realistic silhouettes;
- plausible body dimensions;
- more natural materials/clothing colors;
- better contrast against the ground;
- multiple appearance variants.

Avoid representing people primarily as:

- thin cylinders;
- crude capsules;
- simple rectangular blocks;
- identical repeated stick-like figures.

If existing local person assets are too primitive, improve the human asset pool using better-quality, permissively licensed human models that remain technically manageable in Gazebo.

Do not massively increase polygon count if it breaks generation speed, but move to a meaningfully better-quality human representation.

---

## 4. VEHICLE VISUAL QUALITY IMPROVEMENT

Cars, trucks and buses should be more visually recognizable as vehicles.

Avoid overly abstract "colored box" representations whenever possible.

Improve assets so that vehicles have more believable:

- proportions;
- silhouettes;
- roofs / cabins / cargo bodies;
- wheel placement cues if visible;
- material variation;
- color variation.

Vehicles do not need to be ultra-detailed, but they should be less toy-like and easier to distinguish visually from one another.

The dataset should support clearer separation of:

```text id="lq2o2a"
car
truck
bus
```

not just "small box", "medium box", "long box".

---

## 5. TERRAIN / BACKGROUND REALISM

Current terrain appearance is too flat and repetitive.

Improve backgrounds so grass, dirt, road and mixed scenes look more believable from above.

Use better material/texture quality and more natural variation in:

- color;
- local texture detail;
- roughness/normal response if supported;
- patchiness;
- surface irregularity;
- dirt/grass transitions;
- road-edge appearance.

Avoid backgrounds that look like:

- flat monotone green planes;
- flat brown noise fields;
- perfectly uniform roads with no variation.

The `mixed` background should look like an actual combination of terrain types rather than a simple patch switch.

---

## 6. PBR / MATERIAL IMPROVEMENTS

Where Gazebo Harmonic and the chosen rendering path support it, use improved material definitions such as:

- PBR materials;
- better albedo textures;
- roughness / metalness where suitable;
- normal maps if practical;
- less flat diffuse-only appearance.

Do not add material complexity that destabilizes generation.

Prefer the highest visual-quality materials that remain reliable in headless generation.

Document what the rendering stack actually supports.

---

## 7. LIGHTING AND SHADOW REALISM

Lighting must continue to use the existing families:

```text id="jd7x4z"
morning
noon
evening
shadow
```

but their appearance should become more visually believable.

Improve:

- sun direction consistency;
- softer/more natural shadow placement where supported;
- light color realism;
- ambient light balance;
- contrast between lit and shaded regions;
- reduced "flat game-scene" appearance.

Shadow scenes must produce believable cast shadows from trees, walls, poles or structures.

Do not make realism depend only on darkening the whole image.

---

## 8. HUMAN + SHADOW + OCCLUSION REALISM

Since humans are the priority class, improve realism specifically for humans in realistic outdoor conditions.

Include believable examples of people:

- standing in open sunlight;
- partly under tree shadow;
- near vehicles;
- beside roads;
- near grass/dirt boundaries;
- partly occluded by vehicles/trees/poles;
- in small groups;
- in larger groups.

These should look like plausible aerial observation scenes rather than randomly scattered icons.

---

## 9. SCENE CONTEXT IMPROVEMENT

Make scenes feel more like small outdoor environments and less like sparse object-placement tests.

Without turning the dataset into a cluttered mess, improve realism using plausible context objects such as:

- trees;
- bushes/vegetation;
- rocks;
- poles;
- crates;
- roadside objects;
- barriers;
- small structures;
- road edges;
- terrain transitions.

Context objects must not dominate the scene, but they should help the images resemble actual environments.

---

## 10. OBJECT-GROUND CONTACT REALISM

Ensure all targets sit naturally on the ground.

Avoid:

- floating objects;
- visibly intersecting terrain;
- unnatural object tilt;
- obviously artificial placement;
- shadows inconsistent with object position.

Vehicles should appear naturally placed on plausible surfaces.

Humans should appear grounded and not embedded or hovering.

---

## 11. HUMAN-FOCUSED REALISM REQUIREMENT

Because future detection of humans is a specific priority, improve realism for person examples across:

- single-person scenes;
- multi-person scenes;
- person + vehicle scenes;
- near / medium / far scenes;
- occluded scenes;
- shadow scenes;
- road / grass / dirt / mixed backgrounds.

The human emphasis previously requested still applies:

- more training images containing humans;
- both single-human and multiple-human scenes;
- varied crowd sizes;
- varied human distances and viewpoints.

Do not trade off person-frequency improvement against image-quality improvement.

Both are required.

---

## 12. ASSET UPGRADE POLICY

If the current locally generated assets are the main reason the scenes look too toy-like, prioritize upgrading the asset pool.

For any upgraded asset, record:

- source;
- license;
- checksum;
- local path;
- model scale;
- whether used in train/val/test.

Prefer permissively licensed assets suitable for academic use.

If some existing primitive assets must remain temporarily, document which classes are still visually weak and why.

Do not falsely describe primitive placeholder assets as realistic.

---

## 13. RENDER-QUALITY IMPROVEMENTS

Investigate safe rendering-quality improvements that remain compatible with headless throughput goals.

Examples may include:

- anti-aliasing improvements if supported;
- more stable shadow quality;
- reduced jagged edges;
- improved texture filtering;
- reasonable rendering resolution consistency;
- reliable camera output quality.

Do not make rendering so expensive that dataset generation becomes impractical.

Maintain a balance between:

```text id="3l7h7u"
visual quality
generation speed
reliability
```

If a higher-quality setting reduces throughput, measure the tradeoff and document it.

---

## 14. REALISM QA REQUIREMENT

Add explicit visual QA for realism, not just annotation correctness.

During smoke and pilot review, assess:

- whether humans look recognizably human;
- whether vehicles look recognizably like their class;
- whether backgrounds still look too flat or repetitive;
- whether lighting/shadows look believable;
- whether mixed scenes look like plausible aerial snapshots.

Create a dedicated contact sheet for:

```text id="7xv9se"
best-quality representative scenes
human-focused scenes
single-person scenes
multi-person scenes
person + vehicle scenes
shadow scenes
occluded scenes
```

Also keep a small contact sheet of:

```text id="j4f0f4"
lowest-fidelity / most toy-like scenes
```

so weaknesses are documented honestly.

---

## 15. REALISM ACCEPTANCE CHECK

Add a qualitative acceptance check:

The smoke/pilot dataset must not be approved for full generation if the images still overwhelmingly look like crude abstract toy scenes.

Before full generation, inspect representative samples and explicitly judge:

```text id="k2jtfv"
human recognizability
vehicle recognizability
terrain realism
lighting realism
shadow realism
overall scene plausibility
```

If clearly inadequate, improve assets/materials/rendering first, then regenerate the smoke/pilot stage.

Do NOT proceed to large-scale full generation merely because the labels are technically correct.

---

## 16. DO NOT OVERSHOOT THE CLAIM

Even after realism improvements, documentation must still state:

- the dataset is synthetic;
- the imagery is more realistic than the earlier primitive version;
- the dataset is not equivalent to true real-world aerial imagery;
- better visual fidelity is intended to reduce the synthetic-domain gap, not eliminate it.

Do not claim photorealism unless it is genuinely achieved and defensible.

---

## 17. PILOT REPORTING ADDITION

During the pilot-dataset report, add a section specifically covering:

```text id="36lxs7"
human visual quality improvements
vehicle visual quality improvements
background/material improvements
lighting/shadow improvements
remaining synthetic appearance limitations
speed vs realism tradeoffs
```

State plainly what improved and what still remains simplified.

---

## 18. FULL-DATASET ACCEPTANCE ADDITION

Add the following additional acceptance requirements:

1. Human assets are visually more recognizable than the earlier toy-like baseline.
2. Vehicles are visually more recognizable and class-distinguishable.
3. Backgrounds no longer rely mainly on flat simplistic appearance.
4. Lighting/shadows are more believable than the earlier baseline.
5. The dataset includes human-focused realistic scenes:
   - single-human
   - multi-human
   - person + vehicle
   - shadowed human
   - occluded human
   - small/far human
6. The generator preserves acceptable throughput after realism improvements.
7. Documentation clearly distinguishes:
   - improved realism
   - remaining synthetic limitations.

The objective is to reduce the visual gap between the current primitive synthetic images and more believable aerial-observation imagery, while still preserving reproducibility, automatic labels and efficient dataset generation.