# V0.3 comparison and migration plan — 2026-10-04

## A. Already done

- Verified V0.2 freeze tag and Git history.
- Existing adapter reuses the UAV FSM rather than duplicating it.
- Measured PX4 telemetry drives DroneState; ROS sends position intent and PX4 RTL.
- ENU/NED conversion, versioned topics, finite/bounded setpoints, telemetry freshness, estimator reset checks, PX4 failsafe/mode override handling, battery and measured landing/disarm.
- Human HOLD keeps a later RETURN available, pause preserves the prior phase.
- Eight adapter boundary tests pass with real pinned px4_msgs types (sandbox networking warnings; DDS runtime pending).
- Matching px4_msgs is built; DDS agent is built.
- Deterministic detector with per-drone seeded RNG; launch YAML and durable deployment fixes.
- Existing V0.2 target lifecycle/assignment reservation and mission completion fixes.

## B. Partially done

- PX4 source compilation: whitespace in the current absolute path breaks upstream DDS-client flags.
- One-UAV launch composition exists, but deployment readiness, a queued LAUNCH and reproducible agent/SITL startup are missing.
- PX4 command retries exist; acknowledgement/source correlation and timeout recovery need tighter tests.
- Map origin and bounded search coverage need explicit configuration.
- Standalone adapter import/build tests pass; real PX4 takeoff/search/standoff/HOLD/RTL are pending.

## C. Not started

- QGroundControl telemetry validation.
- Two/eight-UAV flight validation, identity/namespace and performance checks.
- Custom PX4 world and calibrated map camera projection.

## D. Reference items not copied

The reference duplicates the complete UAV FSM, omits telemetry staleness/reset guards, sends the Offboard/arm sequence once, loses unready LAUNCH requests, infers docking from disarm alone, and retains older deployment and mission defects. These are regressions relative to current work. Retain our adapter, freeze history and tests. Camera reference code is functionally identical to the V0.2 approximate projection, so it is not evidence of map-frame geolocation.

## E. Actual bugs/gaps to fix

- LAUNCH must be retained until fresh telemetry/preflight readiness and cancellable by mission overrides.
- Deployment must use the configured active IDs and wait for readiness in PX4 mode.
- A PX4-mode pause/abort must remain effective even before telemetry arrives.
- Landed/RTL completion needs fresh measured landing/disarm; current implementation already preserves this.
- Initial takeoff goal requires spawn/map origin and relative home altitude handling.
- Search lanes need a bounded area; a long mission currently increases lane offset indefinitely.
- Fleet structural configurations can be added, but runtime remains gated 1 -> 2 -> 8.
- Optional LAND can use an adapter-specific typed service without altering frozen DroneCommand.

## Migration/cleanup

Retain all current V0.3 source and Git history in the user-confirmed destination. Preserve the supplied reference separately. Build again from the destination; existing build caches contain absolute paths and must not be treated as portable. Move dependency sources to one destination, preserving pins. Restore the old V0.2 checkout to its verified tag after the migration is verified. Remove duplicate generated build/install/log trees, Python caches and failed build caches. Retain sources, interfaces, assets, docs, test evidence and .git. Write an exact cleanup inventory and before/after size report.

## Completed delta after migration

The initial categories above record the pre-merge audit. The necessary readiness/queued launch/override/origin/search/docking/dependency/runtime gaps are now implemented and tested. One PX4 target mission and no-target mission pass in the new wildlife world, QGC connects and RViz markers remain live. The independent logical eight-UAV demo still passes. The custom world required barometer and navigation sensor plugins, now fixed. The duplicate reference FSM/weak command sequencing/early docking remain deliberately excluded. Two/eight launch composition is structural only; fleet flights, physical UGV composition and calibrated camera perception remain later work. See V0_3_VALIDATION.md for final statuses.
