# -*- coding: utf-8 -*-
"""Commit and push project-wide cleanup via subprocess."""
import subprocess, sys

REPO = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge"
BRANCH = "paper/kbs-verified-20261119"

def run(*args):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(">", " ".join(args[:3]), "...")
    if r.stdout.strip():
        print(r.stdout.strip()[:1200])
    if r.returncode != 0:
        print("STDERR:", r.stderr.strip()[:1200])
        sys.exit(r.returncode)
    return r

run("git", "add", "-A")
run("git", "commit", "-m",
    "chore: remove outdated test rounds and legacy paper workspaces\n\n"
    "- Delete CIKM-era paper workspaces (root tex/, paper_demo/),\n"
    "  TEST-RESULTS, vibe_images, garden-gpt-image-2, skills-archive,\n"
    "  build_librarian judge batches, .bench_backup_20260917\n"
    "- review/: keep only the 4 evidence dirs referenced by the paper's\n"
    "  experiment-source-map (experiment-redesign-20261101, _exp_rerun_20261114,\n"
    "  e2e-master-20261117, api-harness-e2e-20261118); drop 13 historical\n"
    "  acceptance/demo/audit rounds\n"
    "- Remove root temp files, typecheck logs, stale experiment index md;\n"
    "  sweep __pycache__\n"
    "- Include api-web/agentworkshop doc updates from the api-harness session")
run("git", "push", "origin", BRANCH)
run("git", "status", "--short")
print("CLEANUP COMMIT + PUSH OK")
