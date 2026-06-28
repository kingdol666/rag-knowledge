# -*- coding: utf-8 -*-
"""
kb-mcp client - interactive MCP client.

Connects to the kb-mcp server over stdio, lists tools, and can call
any tool via CLI args. Uses the official mcp Python SDK client.

Usage:
  python client.py                         # list all tools
  python client.py health_check            # call a tool with no args
  python client.py kb_search query=test    # call with args
  python client.py kb_doc_create kb_id=mykb name=doc.md content=hello
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import config

SERVER_PATH = str(Path(__file__).parent / "server.py")


def _build_env():
    env = dict(os.environ)
    env.setdefault("WEB_URL", config.WEB_URL)
    env.setdefault("BACKEND_URL", config.BACKEND_URL)
    return env


def _args_str(args):
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


async def _run(tool_name, tool_args):
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
        env=_build_env(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(f"Connected to kb-mcp server | {len(tools)} tools available")

            if tool_name is None:
                for t in sorted(tools, key=lambda x: x.name):
                    print(f"  {t.name}")
                print()
                print("To call a tool: python client.py <tool_name> [key=value ...]")
                print("Example: python client.py kb_search query=wind")
                return

            tool = next((t for t in tools if t.name == tool_name), None)
            if tool is None:
                print(f"ERROR: tool '{tool_name}' not found.")
                print(f"Available: {', '.join(sorted(t.name for t in tools))}")
                sys.exit(1)

            coerced = {}
            for key, val in tool_args.items():
                schema = tool.inputSchema.get("properties", {}).get(key, {})
                ttype = schema.get("type", "string")
                if ttype == "boolean":
                    coerced[key] = str(val).lower() in ("true", "1", "yes")
                elif ttype == "integer":
                    try:
                        coerced[key] = int(val)
                    except ValueError:
                        coerced[key] = val
                elif ttype == "array":
                    coerced[key] = [v.strip() for v in str(val).split(",")]
                else:
                    coerced[key] = val

            print(f"\nCalling: {tool_name}({_args_str(coerced)})")
            result = await session.call_tool(tool_name, arguments=coerced)

            print("RESULT (error):" if result.isError else "RESULT:")
            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)
                else:
                    print(content)


def parse_args(argv):
    if not argv:
        return None, {}
    tool_name = argv[0]
    args = {}
    for token in argv[1:]:
        if "=" in token:
            key, val = token.split("=", 1)
            args[key.strip()] = val
    return tool_name, args


def main():
    tool_name, tool_args = parse_args(sys.argv[1:])
    try:
        asyncio.run(_run(tool_name, tool_args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
