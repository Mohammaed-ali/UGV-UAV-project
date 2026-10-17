# KUKA UGV vertical carousel — Fusion manufacturing design brief

## Current instruction: review and plan first

I want to develop a manufacturable vertical carousel that carries, launches and recovers eight UAVs on an off-the-shelf KUKA unmanned ground vehicle.

This is a separate mechanical design stage based on my existing browser simulation. First read this brief and give me a concise design plan, the principal feasibility risks and the few missing inputs that genuinely block sizing. Do not modify any Fusion document or begin detailed CAD until I connect the Autodesk Fusion MCP and explicitly tell you to start. Once connected, use its actual advertised capabilities; do not invent MCP tools or claim access to a model you have not inspected.

The intended result is a complete, editable mechanical assembly and an engineering package suitable for prototype fabrication after its stated checks and unresolved inputs have been reviewed. A visually convincing CAD model alone is not a manufacturing release.

## 1. Workspace and reference boundaries

All new local files belong under:

`/home/mohammed-ali/Downloads/gpt /Simulation/mechanical_design/vertical_carousel/`

Use explicit absolute paths and this directory as the working directory for write operations. The chat may be attached to the existing “uav ugv project” entry, whose project root is different. That attachment does not authorize edits to that root.

Do not add to or modify:

`/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`

Preserve the running simulation and its source files. Consult these Simulation files read-only when useful:

- `backend/rack.py`: current carousel geometry and simplified motion.
- `README.md`: simulation operating sequence.
- `mechanical_design/vertical_carousel/references/simulation-carousel.png`: visual reference.
- `mechanical_design/vertical_carousel/references/simulation-geometry.json`: extracted reference dimensions and warnings.

The screenshot illustrates the arrangement and appearance. It is not a mechanical drawing, a verified transmission design or evidence that the assembly fits a particular real KUKA platform.

## 2. Functional arrangement to preserve

Use two common square trays, each carrying four UAVs in a 2 × 2 matrix. The trays are vertically stacked when parked. Each UAV has its own docking station, support and positive retention device.

Retain each aircraft’s original tray and bay identity. The conceptual assignment is:

| Bay | Original upper tray A | Original lower tray B |
| --- | --- | --- |
| 1 | UAV 01 | UAV 02 |
| 2 | UAV 03 | UAV 04 |
| 3 | UAV 05 | UAV 06 |
| 4 | UAV 07 | UAV 08 |

Thus the upper matrix is [01, 03; 05, 07] and the lower matrix is [02, 04; 06, 08]. Do not interpret this as drones resting on one another, eight independently moving drawers or an eight-drone single layer.

Both trays must remain horizontal throughout the indexing motion. A platform that simply flips upside down is unsuitable.

Preserve this operating sequence:

1. Transport: A is above B; all occupied docks are positively restrained and the carousel is locked.
2. First deployment: park the UGV, establish the flight safety zone and release selected aircraft from upper tray A.
3. Indexing: after the launch corridor is clear and all remaining aircraft are disarmed and retained, move B to the exposed upper launch/landing station while A moves down.
4. Second deployment: release the selected aircraft assigned to B.
5. Recovery: recover B’s aircraft first onto B at the upper station. Confirm touchdown, motors stopped and retention engaged.
6. Indexing: move loaded B down and A to the upper station, then recover A’s aircraft.
7. Return to transport configuration after checking every occupied dock and the station locks.

Also define partial deployment, interrupted missions, an unavailable aircraft, a failed latch, loss of electrical power and controlled manual recovery. Indexing may have to occur with aircraft still carried on both trays. Check all relevant occupancy patterns, including both fully loaded, one loaded and one empty, and a single occupied corner.

If an aircraft returns out of the preferred sequence, it must wait or use an explicitly designed alternative. It must never land through an obstructing tray or while the carousel is moving.

## 3. Simulation dimensions: reference only

The current simulation uses the following values:

| Item | Simulation value | Interpretation |
| --- | --- | --- |
| Tray plate envelope | 2650 × 2650 × 80 mm | Rendering/physics slab, not selected manufacturing thickness |
| UAV pad block | 1040 × 1040 × 55 mm | Placeholder docking envelope |
| Bay centre offsets | X/Y = ±680 mm | 1360 mm spacing between neighbouring centres |
| Upper/lower tray link origin Z | 2250 / 780 mm | Relative to simulated carrier base_link origin |
| Vertical station separation | 1470 mm | Between tray link origins |
| Simulated carrier origin above ground | 740 mm | Not a KUKA mounting datum |
| Simulated chassis / deck plan size | 3050 / 3220 mm square | Illustrative vehicle, not OEM dimensions |
| Tray centre motion | Y = ±2150 sin(theta) mm; Z = 1515 ±735 cos(theta) mm | Opposed horizontal trays on an elliptical path |

The simulation achieves this motion with coordinated horizontal and vertical prismatic joints. It does not model a finished chain, belt, sprocket or linkage transmission.

At mid-index, the tray-only lateral swept width implied by those values is 2 × 2150 + 2650 = **6950 mm**, before adding UAVs, structure and guarding. This is an engineering issue to resolve, not a dimension to reproduce automatically.

Recalculate the complete arrangement around the actual KUKA mounting interface, allowed footprint, payload, stability and actual UAV envelopes. The simulated tray masses, vehicle mass, actuator settings, 80 mm slab thickness and browser speed settings are not hardware specifications. In particular, the simulation’s selectable 10 m/s UGV speed is not a real KUKA transport requirement.

Keep the visual idea of a square paired-tray carousel where practical. If eight specified UAVs cannot fit within the real platform’s payload and allowable envelope, report that conflict and propose quantified alternatives before proceeding.

## 4. Inspect and simplify the existing KUKA assembly

After I connect the Fusion MCP and authorize starting:

- Discover the supported operations and inspect the active document, design version, units, exact KUKA model, component hierarchy, bodies, occurrences, joints, references and existing timeline.
- Establish vehicle forward, left and up axes, the mounting-plane datum, wheel contact/support geometry and critical interfaces.
- Inventory which geometry is accurate, decorative, incomplete or lacking verified mass/material data.
- Identify mounting holes, structural hard points, battery/service access, charging interfaces, ventilation, emergency stops, safety scanners, cameras and their required fields of view.
- Preserve the original imported assembly. Create a working copy/version or a suitable referenced assembly before modifications, using the capabilities actually available.

“Combine the parts into only the needed parts” means organizing the OEM assembly into useful rigid subassemblies and keeping meaningful joints. Use components, rigid groups and as-built joints where appropriate. Preserve relative motion where it is physically needed.

Do not boolean-union the entire KUKA into one body, delete supplier part identities or merge wheels, rollers, suspension or steering parts that need separate movement. Preserve manufactured-part boundaries required for drawings, service and the bill of materials. Use lightweight reference geometry or suppress cosmetic detail in the working copy when useful. Repeated parts should use reusable component occurrences.

Retain the actual OEM wheel arrangement. The browser model’s four/six-wheel appearance does not require changing an off-the-shelf KUKA chassis.

## 5. Establish a design basis before sizing

Maintain an input register with value, units, source, verification status and consequence if wrong. Separate verified OEM information, measurements from CAD and provisional assumptions.

Obtain or identify:

- Exact UGV model and reliable OEM specifications: rated payload, payload centre-of-gravity limits, mounting interface, allowable loads, permitted operating speed, acceleration, braking and slope with the proposed payload.
- Actual UAV model and mass, battery mass, unfolded and folded rotor envelopes, landing gear geometry, landing tolerances and whether blades remain unfolded while stored.
- Camera position, field of view, focus/detection range and required AprilTag visibility during final approach.
- Maximum transport and operating footprints/heights; indoor/outdoor use, surface conditions, wind exposure, duty cycle and expected cycle life.
- Available electrical supply, continuous/peak power and permitted connection method.
- Workshop processes, preferred stock/materials, budget and whether charging on the carrier is actually required.

The payload budget must include the mounting adapter, frame, mechanism, both trays, all eight aircraft and batteries, drive, restraints, guards, wiring and auxiliary equipment. Do not count only the UAV masses.

Ask a small grouped set of essential questions. If a non-critical value is missing, use an explicitly labelled provisional value for layout studies. Do not release fabricated parts based on unresolved critical dimensions or ratings.

## 6. Select a physically buildable carousel mechanism

Develop a short comparison of plausible mechanisms before committing to detailed CAD. Consider synchronized chain or toothed-belt loops with guided horizontal carriers, a suitable linkage/guidance arrangement, or another compact mechanism that genuinely preserves tray attitude.

For each candidate assess:

- Full swept envelope, clearance between the two trays and aircraft, and clearance from the UGV.
- How horizontal attitude is constrained throughout the complete path.
- Resistance to carrier sway and twisting during landing and asymmetric loading.
- Synchronization of both sides, adjustment, wear, tensioning and failure behaviour.
- Mass, centre-of-gravity excursion, manufacturability, maintenance and available purchased hardware.

Do not present the simulation’s two coordinated sliders as a finished mechanical solution. A simple chain attachment also does not, by itself, prove a tray stays level. Model the actual guidance or anti-rotation constraint.

Size the selected drive and load path: motor, gearbox, shafts, bearings, sprockets/pulleys, chain/belt, couplings, tensioners and support brackets. Include gravity imbalance, acceleration, inertia, friction, transmission efficiency and duty/thermal requirements.

Do not assume the mechanism is balanced: one tray can be fully loaded while the other is empty. Check holding and braking at intermediate positions and on power loss. Provide a suitable anti-drop/retention strategy and positive station locks. Route landing and transport loads into the structure through suitable supports/locks rather than relying on motor holding torque alone.

If lateral sweep or centre-of-gravity movement makes the preferred carousel unsuitable for the actual UGV, identify the conflict early and show a feasible revised layout.

## 7. Build an editable parametric Fusion assembly

Use millimetres, kilograms and newtons consistently. Establish documented datums and user parameters with named relationships, including:

- OEM mounting pattern and protected keep-out regions.
- UAV and rotor envelopes, bay pitch, pad size, tray separation and approach clearances.
- Frame dimensions, carrier guidance geometry and maximum swept footprint.
- Plate/section thicknesses selected from structural checks and available stock.
- Shaft/bearing positions, tension adjustment, indexing positions and lock engagement.
- Maintenance, assembly and fastener tool access.

Organize components around real assemblies, for example:

1. OEM KUKA reference.
2. Mounting adapter and load-spreading structure.
3. Main support frame.
4. Drive, transmission and guidance.
5. Tray A and Tray B.
6. Eight instances of a reusable docking module, with necessary unique marker/identity features.
7. Index locks, sensors and brackets.
8. Guards, covers and service access parts.

Use appropriate joints, limits and motion relationships representing the chosen mechanism’s real degrees of freedom. Keep the feature history understandable and use meaningful part names. Pose animation is useful for communication but is not evidence that a real transmission or safety interlock works.

Prefer stock sections, standard bearings/fasteners and realistic laser-cut, bent, machined, welded or bolted parts. Account for bend radii, weld access/distortion, fits, corrosion protection, drainage, replaceable wear parts and practical assembly order. Avoid arbitrary thin features, inaccessible bolts and unnecessary custom machining.

## 8. Design the docking and launching stations

Each station needs:

- Landing-gear support and a capture/alignment method compatible with the actual UAV.
- Positive transport retention with a defined structural load path and controlled release.
- A means of detecting occupancy, landed/disarmed condition and latch state.
- Clearance for propellers, camera, landing gear, neighbouring aircraft and approach/departure.
- A replaceable, protected and inspectable landing surface.

The upper launch station must have a clear upward flight corridor. Cross-members, locks and guides must not obstruct the rotor envelope or final approach.

Provide unique AprilTag locations for each station. The simulation uses tag36h11, IDs 1–8, with odd IDs on A and even IDs on B. Its approximate marker dimensions are only a reference: select the physical marker size and placement from camera geometry and approach requirements. Check whether the aircraft itself hides the marker before touchdown. Consider additional unobstructed marker locations if necessary.

If charging is approved and the required electrical data is available, include an appropriate protected charging interface and charging/disarm interlock. Do not use an electrical connector as the structural aircraft restraint.

## 9. Integrate controls, service and failure handling

Create a mechanical/electrical interface and state table covering transport, launch-ready, indexing, landing-ready, fault and maintenance states.

Require suitable confirmation of UGV stationary state, carousel index position, mechanical lock engagement, occupancy and restraint before the associated action. Prevent indexing during launch/final approach or while a carried aircraft’s propellers are active.

Include appropriate homing/position sensing, limit protection, guarded pinch points, mechanical stops, power-loss behaviour and controlled manual recovery. Provide maintenance support/locking so a person is not relying solely on an energized drive while working beneath a tray.

Preserve OEM emergency stop access, scanner/camera coverage, maintenance access and vehicle safety functions. Define integration requirements; do not claim that a CAD design or software state table establishes a safety certification.

## 10. Validate the design with stated evidence

Check the full motion cycle, not only the two parked positions:

- Swept-volume interference including all carried UAVs, unfolded rotors, cables, guards, fasteners and tolerance allowances.
- Tray-to-tray clearance, anti-rotation guidance, alignment between both sides and assembly/tension adjustment.
- Station repeatability, landing-surface deflection and lock engagement under load.
- Mass and centre of gravity throughout indexing and all significant occupancy patterns.
- Stability using the actual vehicle support geometry and OEM constraints, including acceleration, braking, turning and permitted slopes.
- Landing impact, transport shock, wind/downwash and the selected operating duty, with a documented basis for each load case.
- Frame stiffness/strength, buckling or fatigue where relevant, joints, fasteners, shaft/bearing life, drive ratings and braking/holding capacity.
- Tolerance stacks and fits at bearings, guides, lock pins and docking interfaces.

Justify design factors and uncertain load assumptions rather than assigning arbitrary factors without context.

Use Fusion analysis only if supported and appropriate. Document material data, connections, mesh, boundary conditions and limitations. If analysis cannot be run, provide reproducible preliminary calculations and identify the checks still required. Do not report unperformed FEA, collision checks, exports or physical tests as passed.

Propose a staged physical test plan: unloaded mechanism, restrained proof/load checks, asymmetric payloads, repeated indexing, power-loss recovery, simulated landing loads, then controlled aircraft trials. Define measurable acceptance criteria from the approved design basis.

## 11. Deliverables and release criteria

Keep outputs in clear subfolders under the mechanical design directory. Produce what the connected tools genuinely support:

- Native editable Fusion assembly, including linked components/archive where appropriate.
- STEP assembly and individual fabricated-part exports.
- Manufacturing drawings with complete dimensions, datums, fits/tolerances, material, finish and relevant weld/bend details.
- DXF profiles/flat patterns and stock cut lists where applicable.
- BOM separating fabricated, purchased and reference/OEM items; quantities, mass and verified supplier data where available.
- Parameter/input registers and mass/payload/centre-of-gravity budgets.
- Mechanism selection rationale, drive/structure/stability calculations and analysis evidence.
- Exploded assembly views, assembly instructions and complete launch/index/recovery motion views.
- Sensor/interlock interface table, risk/failure register, maintenance notes and prototype acceptance plan.
- A clear list of unresolved items and whether each deliverable is concept, prototype-review or fabrication-ready.

Suggested files include `reports/DESIGN_BASIS.md`, `reports/DECISIONS.md`, `parameters.csv`, `BOM.csv`, and folders `calculations/`, `drawings/`, `exports/` and `renders/`.

Do not invent supplier part numbers, material properties, costs, compliance claims or measured results. Respect any imported-model licence. If the MCP cannot perform an operation, explain the limitation and prepare a reviewable alternative supported by the actual Fusion environment.

A release should demonstrate that the exact UAVs fit, the fully equipped assembly is within the verified OEM limits, the mechanism works through its entire stroke, the stations lock and retain aircraft, and the fabricated parts have complete manufacturing information. Record any item that remains unverified.

## 12. Work sequence after authorization

Proceed in useful engineering gates:

1. Inspect the existing assembly and confirm design inputs.
2. Simplify the working assembly into functional components and rigid subassemblies.
3. Compare mechanisms; establish the envelope, payload and stability feasibility.
4. Build the parametric layout and verify complete kinematics.
5. Detail the frame, drive, trays, docks, locks and guards.
6. Perform the available engineering checks and resolve interference/service issues.
7. Prepare the prototype manufacturing and assembly package.

Resolve routine reversible CAD choices within the approved scope. Escalate a change when it materially alters the agreed function, requires modifying the OEM vehicle, exceeds verified platform limits or depends on a critical missing input.

For your first response now, summarize the intended mechanism and launch/recovery order, list the principal engineering unknowns and give the proposed inspection/design plan. Keep this first turn planning-only and wait for my instruction to start work in Fusion.

## Technical reference

Autodesk’s assembly documentation supports organizing non-moving components as rigid groups while preserving the degrees of freedom needed by moving assemblies:

- [Create a rigid group](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CREATE-RIGID-GROUP.htm)
- [Joints in Fusion](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-JOINTS.htm)

Use the exact KUKA model’s official documentation once the model has been identified. No particular KUKA payload, footprint or speed rating is assumed by this brief.
