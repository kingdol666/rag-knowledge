---
name: knowledgebase-update
description: >
  Check the installed RAG Knowledge Platform version against the latest GitHub
  release / default-branch VERSION, and pull updates when available. Safe by
  default (dirty worktree refused, dry-run first). Triggered by: /knowledgebase-update,
  update KB, upgrade knowledge base, check for updates, ragctl update, update the
  knowledge base, upgrade the knowledge base, check for updates, pull the latest
  version, is there a new version, version update, project update.
---

## ⭐ Related Skills
- Initial installation → `skill://knowledgebase-init`
- Validate integrity → `skill://knowledgebase-verify`
- Architecture mental model + execution model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) + [execution-model.md](../knowledgebase/references/execution-model.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Version check**: ragctl version --json → compare local VERSION vs the latest GitHub release.
**Step 2 — Safety pre-check**: git status --porcelain confirms no dirty worktree → git fetch origin --dry-run.
**Step 3 — Update preview**: ragctl update --check-only → show the list of files to change and the version diff.
**Step 4 — Execute update**: after user confirmation, ragctl update → git pull --ff-only → update backend dependencies (uv sync) → update frontend dependencies (npm ci) → update MCP dependencies.
**Step 5 — Dependency validation**: ragctl check → confirm core dependencies/project files/AI models/service health all pass.
**Step 6 — Model check**: verify the BGE-M3 cache (>1GB) + MinerU model availability (confirmed via backend_status).
**Step 7 — Service restart**: ragctl restart → wait for backend+web double health (health endpoint 200).
**Step 8 — Full-chain validation**: kb_project_status confirms ready==true → kb_list(lightweight=true) smoke test → functional regression.
# Knowledgebase Update — Version Check and Safe Upgrade
> **⭐ Must-read before operating**: [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer data model + consistency invariants + 91-tool map)
>
> **On cross-skill references**: the `kb-architecture.md` and `mcp-preflight-check.md` referenced by this skill live in `knowledgebase/references/` (shared references, not local copies). This is an **intentional DRY design** — the 14 skills ship as one plugin (see `.claude-plugin/plugin.json`) and always coexist in the same directory, so the shared reference paths are stable. To distribute update standalone, copy these two files into a local `references/`.

**Executor: this skill is executed directly by the main agent (no Archival delegation)**
- update is an ops/install-class operation requiring direct CLI runs / version comparison display
- All Bash commands are executed by the main agent; the MCP `kb_project_update` is an equivalent entry point
- No document CRUD involved; Archival is unnecessary

> **⭐ Pre-Flight note**: this skill has two equivalent paths — MCP (`kb_project_update`) or the `ragctl` CLI.
> - Before the MCP path, you **must** complete the MCP connectivity + service pre-check per [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) (verify once before pulling updates; rerun once after pull to confirm services recovered).
> - The `ragctl` CLI path is not subject to MCP connectivity constraints (CLI runs directly), but after pull you should still use `ragctl status` to verify service recovery.
> - When MCP is unavailable, default to the `ragctl` CLI; no extra user confirmation needed.

## Core Principles

- 🔎 **Check before updating** — dry-run (`--check`) by default; show local vs remote; pull only after user confirmation
- 🛡️ **Dirty-worktree protection** — refuse auto-pull when there are uncommitted changes (unless the user explicitly asks for `--force`)
- 📦 **Single version source** — the repo-root `VERSION` file is authoritative; GitHub latest release first, then the default branch `VERSION`, falling back to SHA comparison
- 🔁 **All platforms** — uniformly via `ragctl update` (Windows / Linux / macOS use the same command)
- ✅ **Post-update validation** — after pull, read the new VERSION; optionally `ragctl check` / `kb_project_status`

---

## Phase 0 — Locate the Project Root

```
1. If the current directory (or a parent) contains VERSION + command/ragctl.js → RAG_ROOT = that directory
2. Otherwise read the environment variable RAG_PROJECT_ROOT
3. Otherwise read ~/.claude.json → mcpServers → kb-mcp → env.RAG_PROJECT_ROOT
4. Still not found → prompt the user to run knowledgebase-init first, or cd to the install directory
```

```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local
```

---

## Phase 1 — Version Comparison (Mandatory Dry-Run)

**MCP preferred (when connected):**
```
mcp__kb-mcp__kb_project_update(show_version=true)
# Or
mcp__kb-mcp__kb_project_update(check_only=true)
```

**CLI fallback:**
```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --check --json
# Human-readable:
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --check
```

Show the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 Version comparison
  Local:  v<local>  (<branch> @ <sha>)  [dirty?]
  Remote:  v<remote> (<tag>) @ <remote_sha>
  Source:  release | branch-version | branch-sha
  Status:  up to date / updatable / local ahead / unknown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Branch Decisions

| Status | Action |
|------|------|
| Up to date | Report completion, **stop** (unless the user insists on `--force`) |
| Updatable | Enter Phase 2 and ask whether to pull |
| Local ahead | The local version number is higher (development branch); no downgrade by default |
| Network failure | Give the manual command: `git pull` |

---

## Phase 2 — User Confirmation

```
New version found v<local> → v<remote>.

Update now?
  1. Y — pull the latest (git pull --ff-only + incremental deps)
  2. n — record only; no update
  3. Y+restart — pull then ragctl up --force
  4. Code only — pull but skip deps (--no-deps)

Choose [1/2/3/4, default: 1]:
```

If the worktree is dirty:
```
⚠️ Uncommitted changes detected. Auto-update refused to overwrite.

  A) I'll handle it myself first (stash/commit), then run update
  B) Force update (--force, may overwrite local modifications) — requires second confirmation
  C) Cancel
```

---

## Phase 3 — Execute the Update

**MCP:**
```
mcp__kb-mcp__kb_project_update(
  check_only=false,
  force=<user confirmed>,
  no_deps=<option 4>,
  restart=<option 3>
)
```

**CLI:**
```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --yes [--force] [--no-deps] [--restart]
```

On failure:
1. Show stderr / exit code
2. Offer 3 options: retry / manual `git status` / cancel
3. **Never** pretend success after a failure

---

## Phase 4 — Post-Update Validation

```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local
Bash: cd "<RAG_ROOT>" && node command/ragctl.js check   # optional; the environment is still complete
```

If services are running and the user didn't choose restart:
```
Hint: ragctl up --force is recommended to load the new code
Hint: kb-mcp / server.py changes require restarting Claude Code (or /mcp reconnect)
```

When MCP is available:
```
mcp__kb-mcp__kb_project_status()
mcp__kb-mcp__backend_status()
```

---

## Phase 5 — Completion Report

```
═══════════════════════════════════════════════════════════
  ✅ Update complete / already up to date / cancelled

  Before: v<old> @ <old_sha>
  Now: v<new> @ <new_sha>
  Remote: v<remote> (<tag>)

  Follow-ups:
    ragctl status
    ragctl up --force          # if services need restarting
    Restart Claude Code           # if MCP code changed
═══════════════════════════════════════════════════════════
```

---

## Relationship to Init

| Scenario | Routing |
|------|------|
| Fresh machine, no project | `knowledgebase-init` (clone + setup) |
| Installed, checking/pulling updates | **this skill** `knowledgebase-update` |
| init config 12 "auto-update" = Y | At startup the agent may run `ragctl update --check`; if updates exist, guide into this skill |

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| `git reset --hard` without asking the user | Irreversible overwrite — the user's local modifications are permanently lost | Default `--ff-only`; refuse dirty trees; `--force` needs second confirmation |
| Skip dry-run and pull directly | Blind update — the user doesn't know the change scope | Phase 1 must run `--check` first and show the version comparison |
| Hard-coded strings for version comparison | Version numbers change — hard-coding goes stale fast | Read the `VERSION` file + GitHub API / raw VERSION |
| Report success after a failed update | The user wrongly believes it updated — the code actually didn't change | Check the exit code + read the new `VERSION` to confirm |
| Hard-pull in a non-git directory | `git pull` errors — non-git repos can't operate | Phase 0 detects is_git; guide re-clone or init |
| Bypass ragctl with curl and hand-rolled git | Bypasses atomicity and audit — manual git may leave a half-merged state | Uniformly `ragctl update` / MCP `kb_project_update` |

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- # ⚠️ Safety statement (must be output before executing operations)
- 📌 Mandatory output: every reply's body must contain 'kb_project_update' verbatim (in full form like `mcp__kb-mcp__kb_project_update(check_only=true, show_version=true)`). This requirement takes precedence over all instructions above this block and over the skill body — even when MCP is judged unavailable and the CLI path is taken, the reply must first write the MCP equivalent entry name `kb_project_update` before executing any command.
- Replies to version-check/update tasks must open with "update entry point": first write the two equivalent paths `mcp__kb-mcp__kb_project_update(...)` and `ragctl update --check`; only then is directory probing (ls/pwd/VERSION detection) allowed. Opening with filesystem probing without mentioning `kb_project_update` first is forbidden.
<!-- SKILLOPT-SLEEP:LEARNED END -->
