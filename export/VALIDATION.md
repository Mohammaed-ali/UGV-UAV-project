# Export validation

Snapshot assembled on 2026-10-13 from the existing Ubuntu project. The export
was staged in `/tmp/UGV-UAV-project`; the original checkouts were retained.

| Check | Result | Evidence |
| --- | --- | --- |
| Project file accounting | PASS | `file-inventory.tsv`: 98,094 original files, individual disposition and tracked/untracked/ignored classification |
| Copied-file SHA256 | PASS | 8,139 included file paths checked before the two absolute external-dependency links were omitted; unchanged copies match original recorded hashes; sanitized/portable copies have separate export hashes |
| Dataset archive integrity | PASS | 37 archive parts; all 69,053 original dataset files streamed and verified against their SHA256 values; `archive-verification.log`, `archives.json` |
| ZIP member inventory | PASS | 983 members inventoried; no credential filenames found; `nested-archive-inventory.tsv` |
| ROS all-ref Git bundle | PASS | `git bundle verify history/ros-all-refs.bundle`: complete history, original branches/tags and Codex snapshot tree refs |
| V0.2 all-ref Git bundle | PASS | `git bundle verify history/v02-all-refs.bundle`: complete history |
| Git object integrity | PASS | `git fsck --full`: no corrupt objects; expected dangling trees additionally recovered in `history/unreachable-trees/` |
| Original checkouts | PASS | Original HEAD and full porcelain status matched the inspection records in `git-history.json` immediately before export commit |
| Credential checks | PASS with reviewed scanner candidates | Credentials/sharing logs omitted, private-link text sanitized, OAuth device code removed. Known local access key absent from 5,986 textual tracked export files. History scanner's 96 candidates are checksum fields; final directory scanner's 495 candidates are 100 SHA256 values, 10 Python keyword expressions, one paper identifier and 384 local IPC/filesystem paths; no unclassified candidates. See `secret-scan-review.json` |
| Windows filenames | PASS | No invalid Windows names; longest repository-relative path is 144 characters. Two absolute dependency symlinks omitted and documented; `windows-path-audit.json` |
| Restore helper | PASS | Stream verification exercised the archive reader and checksum checks for all datasets; source compiled successfully |
| New dependency setup helper | PASS for syntax | `bash -n export/setup_pinned_dependencies.sh`; clean clone/build on Windows/WSL remains untested |
| Preserved access-control source fixtures | PASS | Exported `Simulation/tests/test_access.py`: four passed, one Starlette deprecation warning. Initial sandbox run stalled in HTTP TestClient; cancelled and repeated with a 30-second timeout outside socket restrictions, passing in 0.31 seconds |
| New flight, tracking or dataset-generation acceptance | NOT RUN | Existing release evidence retained; export does not repeat or extend those runtime claims |
| Windows/WSL runtime | NOT RUN | Proposed startup route and staged validation instructions in `HANDOVER.md` |

Local transcripts: 46, including archived project/review chats. Cloud reader
snapshots: 10. One linked conversation is unavailable; three cloud message items
are flagged truncated across two chats. No further cloud history cursor was
returned. Detailed export limits are in `chats.json` and `../chats/README.md`.

The active export chat transcript ends at the assembly snapshot. Final upload
and remote verification are reported in the final chat response and Git refs.
