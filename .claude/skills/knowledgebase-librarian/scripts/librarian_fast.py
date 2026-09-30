#!/usr/bin/env python3
"""REMOVED 2026-09-28 — do not resurrect.

This script used to run the librarian lane (L0→L6) end-to-end in one command.
It was removed because it let harnesses shortcut the skill contract:

  1. The agent never executed the catalog → description → trust → read → judge
     flow the knowledgebase-librarian skill exists to guarantee.
  2. It self-fetched the MCP auth token from .env / storage/loop-auth.json and
     spawned its own MCP client, bypassing the host's MCP governance.

The librarian lane is executed BY THE AGENT, layer by layer, through the
host-provided MCP tools:

  kb_list → kb_get_documents → kb_doc_read → kb_laya_judge → synthesize

Read .claude/skills/knowledgebase-librarian/SKILL.md ("Execution contract")
and follow it. Judging goes through the kb_laya_judge MCP tool. An archived
copy of the removed implementation lives at
skills-archive/librarian_fast.py.removed-20260928 (reference only — do not run).
"""
import sys

sys.stderr.write(
    "librarian_fast.py was removed 2026-09-28: end-to-end scripts bypass the\n"
    "skill contract and MCP governance. Execute the librarian lane yourself via\n"
    "MCP tools (kb_list → kb_get_documents → kb_doc_read → kb_laya_judge) per\n"
    ".claude/skills/knowledgebase-librarian/SKILL.md.\n"
)
sys.exit(3)
