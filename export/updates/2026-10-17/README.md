# Simulation and KUKA/Fusion archive update — 17 October 2026

This update continues GitHub `main` from `38379db0eeb4a9b97e6fa9c492690772857b52aa`.
It refreshes the independent `Simulation/` project and its associated chats. The
original ROS workspace, original Simulation folder, earlier repository history,
dataset archives and prior validation evidence are preserved.

## Included

- **Simulation:** 244 new or changed source, configuration, mechanical-planning
  and evidence files. Current source files were compared with the existing
  export; 4,301 included files were already identical. The complete supplemental
  inventory covers 19,680 local files, including ignored/cache/runtime files.
- **Close approach:** overhead approach and hold, adjustable minimum clearance,
  image/depth pairing, identity continuity, backoff, operator controls and tests.
  No spray or delivery action or visual effect was added. Passing and failed
  native attempts, screenshots, compact telemetry and available PX4 logs are
  retained under `Simulation/artifacts/close-approach/` and `artifacts/runs/`.
- **Startup heading:** the UGV and eight docked aircraft start facing the first
  route segment. The retained native result records approximately zero startup
  rotation, 0.445 m arrival error and unchanged saved mission settings.
- **Mechanical planning:** `Simulation/mechanical_design/vertical_carousel/`
  contains the design brief, simulation geometry register and reference image.
  Simulation dimensions are reference geometry, not manufacturing specifications.
- **[KUKA UGV vertical carousel — Fusion…](../../../chats/local/01a13ffb-48fc-7672-b87a-4e980a0cdbf6.md):**
  the complete available local assistant discussion and tool records. Its stored
  session has no initial standalone user request; the saved design brief preserves
  that context. The session reviewed feasibility only. No Fusion CAD exists from
  this session, and connecting Fusion and authorizing CAD work remain separate steps.
- **[Plan browser simulation prompt](../../../chats/local/01a112b6-d0f6-7051-a9c7-d522b648c300.md):**
  refreshed across both available session files through 16 October 2026 at
  20:09 Asia/Riyadh, including the close-approach and startup-heading changes.
  The transcript has 331 stored messages and 3,134 tool records. Available pasted
  text attachments are retained under `chats/attachments/`.

The five current production files in `Simulation/dist/` were rebuilt and match
the local production bundle byte for byte; three obsolete generated assets were
removed so the served interface uses the current code.

Tool records live separately under `chats/tools/`. Large files use Git LFS.
Local transcripts remain readable files and do not import as live Codex chats.
Stored output truncation is retained. System/developer prompts, internal reasoning,
credential values and temporary private sharing links are excluded or redacted.

## Verification

- **PASS:** all 4,545 included Simulation source-file SHA256 values still match
  the original local files; staged LFS objects match their SHA256 object IDs.
- **PASS:** 153 backend tests and three frontend tests on the temporary export.
- **PASS:** TypeScript and Vite production builds. Vite retains its existing
  advisory about the large scene bundle.
- **PASS:** original ROS HEAD, Git refs and uncommitted-file status unchanged.
- **PASS with reviewed candidates:** gitleaks directory scan; 495 candidates
  were checksum fields, filesystem paths or Python expressions. No unresolved
  candidates remain. Known local access keys and private share links are removed.
- **NOT RUN:** new flight qualification or a Windows/WSL runtime. The existing
  close-approach result covers one UAV and one slow-moving car: 8.02 seconds of
  hold, 0.6105 m minimum evaluated clearance, backoff, return, landing, disarm and
  latch. Other target classes and faster/dense traffic remain unqualified.

`verification.json`, `summary.json`, `new-lfs-objects.json` and
`simulation-file-inventory.tsv` record the checks, exact file scope and hashes.
The original root `export/*` inventories continue to describe the 13 October
snapshot; this directory supplements them for the refreshed paths.

## Exclusions and portability

The supplemental inventory records 15,135 omitted files: installed Python and
frontend dependencies, compiler caches, live `.runtime/` state and private
sharing/authentication state. Durable flight and validation evidence in
`artifacts/` is included, even when ignored by the development workspace.
Historical runtime diagnostics already in GitHub remain historical evidence.

The existing export-relative reference in `Simulation/scripts/prepare_assets.py`
is preserved so its optional asset helper can use this combined repository.
All original local files retain their original bytes and paths.

On an existing Windows clone, run `git pull` and `git lfs pull`, then read the
root `HANDOVER.md` and `chats/README.md`. Runtime dependencies still require the
Linux/WSL setup described in that handover.
