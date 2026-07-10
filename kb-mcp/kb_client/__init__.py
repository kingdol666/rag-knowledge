"""kb_client - decoupled HTTP client for the RAG Knowledge Platform API.

This package wraps every knowledge-base HTTP endpoint into typed async
methods on a single KbClient class. It has zero MCP dependencies, so it
can be reused by the MCP server, test scripts, or any other Python tool.

Usage:
    from kb_client import KbClient
    from config import WEB_URL, BACKEND_URL
    client = KbClient(web_url=WEB_URL, backend_url=BACKEND_URL)
    bases = await client.kb_list()
"""
from kb_client.client import KbClient

__all__ = ["KbClient"]
__version__ = "1.0.0"
