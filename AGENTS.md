# AGENTS.md — Assetize fork of ibm-mas/python-devops

> **HARD RULE — never contribute AI-agent files upstream.**
> This file, `CLAUDE.md`, `.assetize/` and any other AI-agent file (`.claude/`,
> `.cursor*`, `.windsurf*`, `.aider*`, `GEMINI.md`, `.github/copilot-instructions.md`,
> agent prompts/rules/skills/memory/plans we add) are **fork-only**. Never include them
> in a commit, branch or PR targeting `ibm-mas/*`. Upstream's own `AGENT_INSTRUCTIONS.md`
> and `.bob/` belong to IBM — leave them alone unless the upstream change needs it.
> Enforced by a pre-push hook: run `.assetize/install-hooks.sh` once per clone. Never
> bypass it with `--no-verify`.

## What this repo is
- Fork of [`ibm-mas/python-devops`](https://github.com/ibm-mas/python-devops) (default
  branch `stable`). Published upstream as PyPI `mas-devops` (import path `mas.devops`).
- Library consumed by the MAS CLI (fork: `softwarecomparereview/assetize-mas-cli`, see its
  `AGENTS.md` for the end-to-end architecture). The CLI collects input, then calls this
  library to talk to the cluster and launch Tekton PipelineRuns.
- Upstream's own agent guide: `AGENT_INSTRUCTIONS.md` (conventions, layout).

## Map (`src/mas/devops/`)
| Module | Used by the CLI for |
|---|---|
| `ocp.py` | connect, namespaces, storage classes, cluster version, path-based routing |
| `mas/` | MAS instances, channels, current catalog, default storage class detection (`getDefaultStorageClasses`), installed apps |
| `data/` | **Catalog metadata** (per-catalog operator versions, what's new, known issues, OCP compatibility) — `getCatalog`, `getNewestCatalogTag`, `getCatalogEditorial`, OCP lifecycle |
| `tekton.py` + `templates/` | Install OpenShift Pipelines, prepare namespaces/secrets, render & launch PipelineRuns (`launchInstallPipeline`, `launchUpdatePipeline`, …) |
| `aiservice.py`, `sls.py`, `db2.py`, `olm.py`, `users.py`, `backup.py`, `restore.py`, `pre_install.py`, `utils.py`, `slack.py` | Supporting helpers |

**Assetize value:** `src/mas/devops/data/` is the structured source for catalog →
version → OCP compatibility data used by Upgrade Desk / Change Watch.

## Local development
```bash
# a shared venv lives in the CLI fork; it installs this repo editable
/home/user/assetize-mas-cli/.venv/bin/pytest test/src/mock     # mock tests (no cluster)
# test/src/test_*.py mostly need a live cluster
```
- Cross-repo changes use the **same branch name** in cli / python-devops / ansible-devops.
- Commit/PR titles use `[patch]` / `[minor]` / `[major]`.
