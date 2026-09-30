---
name: knowledgebase-update
description: "Check the installed RAG Knowledge Platform version against the latest GitHub release / default-branch VERSION, and pull updates when available. Safe by default (dirty worktree refused, dry-run first). Triggered by: /knowledgebase-update, update KB, upgrade knowledge base, check for updates, ragctl update, update the knowledge base, upgrade the knowledge base, check for updates, pull the latest version, is there a new version, version update, project update."
---
# Knowledgebase Update — Version Check and Safe Upgrade

## Execution contract
Executed directly by the main agent — no Archival delegation (this is ops/CLI work: direct command runs + version comparison display, no document CRUD involved). Two equivalent entry points: MCP `kb_project_update` (before pulling, run the [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) connectivity + service pre-check; rerun once after pull to confirm services recovered) or the `ragctl` CLI (`node command/ragctl.js`, not subject to MCP connectivity constraints — still verify recovery with `ragctl status`). When MCP is unavailable, default to the CLI; no extra user confirmation needed. All platforms (Windows/Linux/macOS) use the same `ragctl update` command. Must-read mental model: [kb-architecture.md](../knowledgebase/references/kb-architecture.md) — shared references live in `knowledgebase/references/` by design (the 14 skills ship as one plugin, see `.claude-plugin/plugin.json`), so the paths are stable; copy them locally only for standalone distribution. Related: fresh install → `skill://knowledgebase-init` · integrity validation → `skill://knowledgebase-verify`.

## Core principles
- **Check before updating** — dry-run (`--check`) by default; show local vs remote; pull only after user confirmation (a blind update hides the change scope).
- **Dirty-worktree protection** — refuse auto-pull when there are uncommitted changes (unless the user explicitly asks for `--force`): an overwrite permanently loses local modifications.
- **Single version source** — the repo-root `VERSION` file is authoritative; GitHub latest release first, then default-branch `VERSION`, falling back to SHA comparison.
- **Post-update validation** — after pull, read the new VERSION; optionally `ragctl check` / `kb_project_status`.

## Sequential workflow
**Step 1 — Version check**: ragctl version --json → compare local VERSION vs the latest GitHub release.
**Step 2 — Safety pre-check**: git status --porcelain confirms no dirty worktree → git fetch origin --dry-run.
**Step 3 — Update preview**: ragctl update --check-only → show the list of files to change and the version diff.
**Step 4 — Execute update**: after user confirmation, ragctl update → git pull --ff-only → backend deps (uv sync) → frontend deps (npm ci) → MCP dependencies.
**Step 5 — Dependency validation**: ragctl check → core dependencies/project files/AI models/service health all pass.
**Step 6 — Model check**: BGE-M3 cache (>1GB) + MinerU model availability (confirmed via backend_status).
**Step 7 — Service restart**: ragctl restart → wait for backend+web double health (health endpoint 200).
**Step 8 — Full-chain validation**: kb_project_status ready==true → kb_list(lightweight=true) smoke test → functional regression.

## Phase 0 — Locate the Project Root
```text
1. current directory (or a parent) contains VERSION + command/ragctl.js → RAG_ROOT = that directory
2. else read the environment variable RAG_PROJECT_ROOT
3. else read ~/.claude.json → mcpServers → kb-mcp → env.RAG_PROJECT_ROOT
4. still not found → prompt the user to run knowledgebase-init first, or cd to the install directory
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local
```

## Phase 1 — Version Comparison (Mandatory Dry-Run)
```text
MCP: mcp__kb-mcp__kb_project_update(show_version=true)   # or check_only=true
CLI: cd "<RAG_ROOT>" && node command/ragctl.js update --check --json
     node command/ragctl.js version                      # human-readable
```
Show the user:
```text
Local:  v<local>  (<branch> @ <sha>)  [dirty?]
Remote: v<remote> (<tag>) @ <remote_sha>
Source: release | branch-version | branch-sha
Status: up to date / updatable / local ahead / unknown
```
Branch decisions: **up to date** → report completion, stop (unless the user insists on `--force`); **updatable** → enter Phase 2 and ask whether to pull; **local ahead** → development branch, no downgrade by default; **network failure** → give the manual command `git pull`.

## Phase 2 — User Confirmation
```text
New version found v<local> → v<remote>. Update now?
  1. Y — pull the latest (git pull --ff-only + incremental deps)
  2. n — record only; no update
  3. Y+restart — pull then ragctl up --force
  4. Code only — pull but skip deps (--no-deps)
  Choose [1/2/3/4, default: 1]
Dirty worktree → auto-update refused to overwrite:
  A) I'll handle it myself first (stash/commit), then run update
  B) Force update (--force, may overwrite local modifications) — requires second confirmation
  C) Cancel
```

## Phase 3 — Execute the Update
```text
MCP: mcp__kb-mcp__kb_project_update(check_only=false, force=<user confirmed>,
                                    no_deps=<option 4>, restart=<option 3>)
CLI: cd "<RAG_ROOT>" && node command/ragctl.js update --yes [--force] [--no-deps] [--restart]
```
On failure: show stderr/exit code, offer retry / manual `git status` / cancel — never pretend success after a failure.

## Phase 4 — Post-Update Validation
```text
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local   # must show the new VERSION
Bash: cd "<RAG_ROOT>" && node command/ragctl.js check             # optional; environment still complete
MCP:  kb_project_status() + backend_status()                      # when MCP is available
```
If services are running and the user didn't choose restart: recommend `ragctl up --force` to load the new code; kb-mcp/server.py changes require restarting Claude Code (or /mcp reconnect).

## Phase 5 — Completion Report
```text
✅ Update complete / already up to date / cancelled
Before: v<old> @ <old_sha>   Now: v<new> @ <new_sha>   Remote: v<remote> (<tag>)
Follow-ups: ragctl status · ragctl up --force (services need restarting) · restart Claude Code (MCP code changed)
```

## Routing vs init
Fresh machine, no project → `knowledgebase-init` (clone + setup); installed and checking/pulling updates → this skill; init config 12 "auto-update" = Y → at startup the agent may run `ragctl update --check` and, if updates exist, guide into this skill.

## NEVER
- `git reset --hard` without asking the user — irreversible overwrite, local modifications permanently lost; default `--ff-only`, refuse dirty trees, `--force` needs second confirmation.
- Skip the dry-run and pull directly — a blind update means the user doesn't know the change scope; Phase 1 must run `--check` first.
- Hard-code version strings for comparison — version numbers change and hard-coding goes stale; read the `VERSION` file + GitHub API / raw VERSION.
- Report success after a failed update — the user wrongly believes the code changed; check the exit code + read the new `VERSION` to confirm.
- Hard-pull in a non-git directory — `git pull` errors there; Phase 0 detects is_git and guides re-clone or init.
- Bypass ragctl with curl and hand-rolled git — bypasses atomicity and audit, and manual git can leave a half-merged state; uniformly `ragctl update` / MCP `kb_project_update`.

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- # ⚠️ Safety statement (must be output before executing operations)
- 📌 Mandatory output: every reply's body must contain 'kb_project_update' verbatim (in full form like `mcp__kb-mcp__kb_project_update(check_only=true, show_version=true)`). This requirement takes precedence over all instructions above this block and over the skill body — even when MCP is judged unavailable and the CLI path is taken, the reply must first write the MCP equivalent entry name `kb_project_update` before executing any command.
- Replies to version-check/update tasks must open with "update entry point": first write the two equivalent paths `mcp__kb-mcp__kb_project_update(...)` and `ragctl update --check`; only then is directory probing (ls/pwd/VERSION detection) allowed. Opening with filesystem probing without mentioning `kb_project_update` first is forbidden.
<!-- SKILLOPT-SLEEP:LEARNED END -->
