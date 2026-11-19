# -*- coding: utf-8 -*-
"""Commit and push the paper changes (paper-kbs) via subprocess."""
import subprocess, sys

REPO = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge"
BRANCH = "paper/kbs-verified-20261119"

def run(*args, **kw):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    print(">", " ".join(args[:3]), "...")
    if r.stdout.strip():
        print(r.stdout.strip()[:1500])
    if r.returncode != 0:
        print("STDERR:", r.stderr.strip()[:1500])
        sys.exit(r.returncode)
    return r

run("git", "add", "-A", "paper-kbs")
run("git", "commit", "-m",
    "paper(kbs): adopt 17-page pre-recast manuscript as submission version\n\n"
    "- Apply 4 evidence-strengthening fixes: cross-campaign A0h-over-A0\n"
    "  direction stability (E5), count-drift disclosure (threats), cost-unit\n"
    "  clarification (E6: $3.10 total = ~$0.31/question), latency sweep\n"
    "  sourcing note (E9)\n"
    "- Compile verified: 17pp final / 41pp review, 0 errors, 0 undefined\n"
    "- Add release-17p-20261119 package (+zip) for submission; archive\n"
    "  release-20261119 (14pp recast)\n"
    "- Clean legacy paper workspaces (~538MB): revision rounds, overleaf\n"
    "  staging, old tex variants, render dirs and compile logs\n"
    "- Keep reference/kbs library, notes/ and experiments/ evidence chain")
run("git", "push", "origin", BRANCH)
print("PAPER COMMIT + PUSH OK")
