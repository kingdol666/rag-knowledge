# -*- coding: utf-8 -*-
"""Clean up duplicate test files created during scenario tests."""
import asyncio
import sys
import os
from pathlib import Path

KB_MCP_DIR = Path(__file__).resolve().parent.parent / "kb-mcp"
sys.path.insert(0, str(KB_MCP_DIR))
os.environ.setdefault("APP_MODE", "dev")

from kb_client.client import KbClient
import config


async def cleanup():
    async with KbClient(web_url=config.WEB_URL, backend_url=config.BACKEND_URL) as c:
        kb_id = "4c1b9eb6-b8d3-498a-b8fa-f96cb7cdfd3b"  # AI-ML-Research
        r = await c.kb_get_documents(kb_id=kb_id)
        docs = r.get("documents", [])
        for d in docs:
            name = d.get("name", "")
            if "paper_attention (" in name:
                path = d.get("path", "")
                print(f"  Deleting: {name} ({path})")
                await c.kb_doc_delete(kb_id=kb_id, doc_path=path)
        print("Cleanup done.")


if __name__ == "__main__":
    asyncio.run(cleanup())
