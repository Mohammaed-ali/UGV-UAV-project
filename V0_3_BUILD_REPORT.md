# V0.3 build report

The confirmed V0.3 folder is now the primary source/build location. All 110 previous tracked files and Git history were retained. Nine ROS packages, pinned PX4 SITL and the XRCE agent build successfully. The independent eight-UAV logic demo and two real single-UAV PX4 mission branches pass. See docs/V0_3_VALIDATION.md for evidence and limitations.

Necessary additions: readiness-aware active deployment, queued LAUNCH, early mission overrides, map origins and relative home altitude, bounded search lanes, configurable expected docking totals, source-correlated ACKs, fault reporting/recovery, pinned dependency paths, owned-process runtime, PX4 wildlife world, reproducible validation and QGC scripts.

No duplicate PX4 mission FSM/package was copied from the supplied reference. Its weaker one-shot command sequencing, unready launch loss, early docking inference and old mission/deployment behavior were not copied. Frozen typed contracts and the deterministic detector/tracker/target/operator architecture are intact.

V0.2 is checked out on its verified branch. Approximately 193 MiB of redundant generated file content was deleted; its total disk usage is now about 1.9 MiB. Upstream sources and usable dependencies were moved to a shared space-free directory rather than deleted. Exact inventory: docs/CLEANUP_REPORT.json. The reference and V0.1 were retained.

The desktop saved project/chat still points at the old V0.2 folder: no supported tool exposes rebinding it. Open/add the confirmed V0.3 folder in the app to change that UI project association; all development commands and files for this milestone already use V0.3.
