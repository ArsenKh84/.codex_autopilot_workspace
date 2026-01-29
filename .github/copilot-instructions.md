# Copilot Instructions — Technoglob Workspace

Purpose: Give AI coding agents concise, actionable rules for working productively in this repository.

Quick Commands
- **Inspect workspace:** `./tg-autopilot doctor` (runs checks, collects env info to /tmp/tg_autopilot_run.log)
- **Open project (mac/dev):** `./tg-autopilot run` (opens Xcode project when present)
- **Run local static server:** `node server.mjs` (listens on port 8000)

Big Picture Architecture
- Predominantly a shell-script-centric ops repo with many top-level automation scripts (deploy-*, install_*, tg_*) and helper tools.
- Small Node static server (`server.mjs`) used for quick local serving. Xcode projects live at top-level when present (used for iOS/mac builds).
- Integrations: Jetson devices and RTX/Docker workflows are driven by a family of `tg_*` scripts (deploy, health, restore), not by a monolithic service.

Developer Workflows & Patterns
- Prefer the repo's existing CLI scripts over ad-hoc commands. Example: use `tg-deploy.sh`, `deploy-to-jetson.sh`, and `tg-autopilot` for system-level tasks.
- Logging: Captain pattern is `exec > >(tee -a "$LOG") 2>&1` (see `tg-autopilot`); preserve logs under `/tmp` or `logs/` when present.
- Language/tools: heavy use of bash + system tools; Node used for small services (`package.json` depends on `openai`), Xcode for native builds.

Project-specific Conventions
- Shell-first: write or update shell scripts for infra tasks; keep behavior deterministic and idempotent.
- Use repository-provided tools (prefix `tg_` or `deploy-`) rather than calling Docker/Xcode directly unless diagnosing.
- When inspecting system state, surface the exact commands run (copyable), capture stdout/stderr with `tee`, and reference the log path.

Integration Points & External Dependencies
- Jetson & device management: many scripts named `jetson-*`, `deploy-to-jetson.sh`, `tg_jetson*` — expect SSH, keys, and device-specific steps.
- RTX/Docker: checks in `tg-autopilot` call `docker ps` and expect Docker to be used behind `tg_*` helpers.
- OpenAI: `package.json` contains `openai` dependency — Node-based automation or services may call OpenAI APIs.

What to change and what to not change
- Preserve the top-level `tg-*`, `deploy-*`, and `install_*` script interfaces; update them only when adding new functionality that complements existing flows.
- Avoid changing VS Code/UI settings in this repo — operations are executed from terminal scripts.

Where to look (examples)
- `tg-autopilot` — workspace doctor, run, status (see logging and entry points)
- `server.mjs` — local static Node server (port 8000)
- `manifest.json` — small example of data files/asset metadata
- `deploy-to-jetson.sh`, `deploy-tg-full.sh`, `tg_deploy.sh` — deployment orchestration

If unsure, do this first
1. Run `./tg-autopilot doctor` and attach the output log.
2. Open `server.mjs` and `tg-autopilot` to confirm side-effects before editing other scripts.

Please review — I can refine examples or add missing script references you want included.
