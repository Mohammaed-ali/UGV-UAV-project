# UAV / UGV project — complete local export

Start with [HANDOVER.md](HANDOVER.md) for the inspected state, Windows access,
dependency reconstruction, startup and remaining validation limits.

This repository preserves the original ROS Git history and adds the local
Fieldlab browser simulation, legacy versions, documents, assets, all available
dataset files, and readable project chat transcripts. The source projects on
Ubuntu were retained.

| Location | Contents |
| --- | --- |
| `src/`, `scripts/`, `docs/`, `tools/synthetic_dataset/` | ROS workspace and completed V0.5 offline dataset tooling |
| `Simulation/` | Independent Fieldlab browser, Gazebo, PX4 and physical carrier prototype |
| `archives/datasets/` | 37 Git LFS archive parts covering final, pilot, smoke, determinism and failed/resumed datasets |
| `legacy/` | V0.1/V0.2 folder snapshots, original ZIPs and complete-source/stage-1 archives |
| `history/` | All-ref Git bundles and recovered dangling Git trees |
| `documents/`, `assets/project-concept-videos/` | Course proposal/template and available concept videos |
| `chats/` | 46 local transcripts, tool records, 10 cloud reader snapshots and available attachments |
| `export/` | File and dependency inventories, checksums, chat limitations and restore tools |

Install Git LFS before cloning. In Windows PowerShell:

```powershell
git lfs install
git -c core.longpaths=true clone https://github.com/Mohammaed-ali/UGV-UAV-project.git
cd UGV-UAV-project
git config core.longpaths true
git lfs pull
```

For a small source-only download, set `$env:GIT_LFS_SKIP_SMUDGE="1"` before the
clone and remove it afterwards with `Remove-Item Env:GIT_LFS_SKIP_SMUDGE`. Then
fetch the required LFS paths when needed. Files still containing LFS pointers
cannot be used as assets or archives.

The root ROS overview is retained in [README_ROS.md](README_ROS.md). Fieldlab's
startup and measured limits are in [Simulation/README.md](Simulation/README.md).
The [chat index](chats/README.md) explicitly identifies unavailable or bounded
history. Transcripts do not automatically become live Codex conversations.
