"""Extend the zero-kb-tool auto re-run to requestMcpMount callers.

The mount flakes ~1-in-6 sessions; kbEnhanced non-stream turns already get
one automatic re-run on the "zero mcp tools used" signature. Benchmark chat
tracks (allowedTools-only) hit the same flake — extend both gates.
"""
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "web" / "server" / "api" / "claude" / "chat.post.ts"
s = P.read_text(encoding="utf-8")

old_max = "    const maxAttempts = kbEnhanced && !streamMode ? 2 : 1"
new_max = "    const maxAttempts = (kbEnhanced || requestMcpMount) && !streamMode ? 2 : 1"
assert s.count(old_max) == 1, f"maxAttempts x{s.count(old_max)}"
s = s.replace(old_max, new_max, 1)

old_saw = "        if (kbEnhanced && message.type === 'assistant') {"
new_saw = "        if ((kbEnhanced || requestMcpMount) && message.type === 'assistant') {"
assert s.count(old_saw) == 1, f"sawKbTool x{s.count(old_saw)}"
s = s.replace(old_saw, new_saw, 1)

old_retry = "      if (!streamMode && finalResult && kbEnhanced && !sawKbTool && attempt < maxAttempts - 1) {"
new_retry = "      if (!streamMode && finalResult && (kbEnhanced || requestMcpMount) && !sawKbTool && attempt < maxAttempts - 1) {"
assert s.count(old_retry) == 1, f"retry x{s.count(old_retry)}"
s = s.replace(old_retry, new_retry, 1)

P.write_text(s, encoding="utf-8")
print("patched retry gates:", P)
