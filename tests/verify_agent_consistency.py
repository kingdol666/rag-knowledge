"""Verify Agent tool list matches MCP server tool definitions exactly."""
import sys
import os
from pathlib import Path

KB_MCP_DIR = Path(__file__).parent.parent / "kb-mcp"
sys.path.insert(0, str(KB_MCP_DIR))

os.environ["APP_MODE"] = "dev"

from server import mcp

# Get actual MCP tools
mcp_tools = sorted(mcp._tool_manager._tools.keys())
mcp_set = set(mcp_tools)

# Parse agent tools from knowledge-admin.md
agent_file = KB_MCP_DIR.parent / ".claude" / "agents" / "knowledge-admin.md"
with open(agent_file, encoding="utf-8") as f:
    lines = f.readlines()

agent_tools = []
for line in lines:
    line = line.strip()
    if "mcp__kb-mcp__" in line:
        # Extract tool name: mcp__kb-mcp__tool_name
        tool = line.replace("mcp__kb-mcp__", "").strip().lstrip("-").strip()
        if tool and not tool.startswith("#"):
            agent_tools.append(tool)

agent_tools = sorted(set(agent_tools))
agent_set = set(agent_tools)

# Compare
missing_in_agent = mcp_set - agent_set
missing_in_mcp = agent_set - mcp_set

print(f"MCP server tools:  {len(mcp_tools)}")
print(f"Agent file tools:  {len(agent_tools)}")
print(f"Match: {'YES' if not missing_in_agent and not missing_in_mcp else 'NO'}")

if missing_in_agent:
    print(f"\n[ERROR] Tools in MCP but NOT in agent file ({len(missing_in_agent)}):")
    for t in sorted(missing_in_agent):
        print(f"  - {t}")

if missing_in_mcp:
    print(f"\n[ERROR] Tools in agent file but NOT in MCP ({len(missing_in_mcp)}):")
    for t in sorted(missing_in_mcp):
        print(f"  - {t}")

if not missing_in_agent and not missing_in_mcp:
    print("\n[PASS] Agent tool list matches MCP server 100%!")

# Also verify skills listed in agent
skill_lines = []
in_skills = False
for line in lines:
    stripped = line.strip()
    if stripped == "skills:":
        in_skills = True
        continue
    if in_skills:
        if stripped.startswith("- "):
            skill_lines.append(stripped.lstrip("- ").strip())
        elif not stripped.startswith("-") and stripped and not stripped.startswith("#"):
            break

print(f"\nAgent skills: {skill_lines}")

# Check skill directories exist
skills_dir = KB_MCP_DIR.parent / ".claude" / "skills"
existing_skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
print(f"Skill directories with SKILL.md: {sorted(existing_skills)}")

missing_skills = [s for s in skill_lines if s not in existing_skills]
extra_skills = [s for s in existing_skills if s not in skill_lines and s != "knowledgebase"]

if missing_skills:
    print(f"\n[ERROR] Skills in agent but no directory: {missing_skills}")
if extra_skills:
    print(f"\n[WARN] Skills with directory but not in agent list: {extra_skills}")
if not missing_skills:
    print("\n[PASS] All agent skills have corresponding directories!")
