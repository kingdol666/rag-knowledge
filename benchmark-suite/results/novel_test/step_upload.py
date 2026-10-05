#!/usr/bin/env python3
"""Upload the 26 novel parts into the KB via kb_doc_create (real MCP calls)."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
PARTS_DIR = SUITE / "data" / "novels" / "parts"
KB_ID = "b4c48237-6937-440a-9696-cc1e66bed5c1"
TAGS = ["Pride and Prejudice", "Jane Austen", "English novel", "classical literature"]

CH_RE = re.compile(r"\bChapter\s+([IVXL]+)\b")


def chapter_range(text: str) -> str:
    chs = CH_RE.findall(text)
    if not chs:
        return ""
    return f"Chapter {chs[0]}–{chs[-1]}"


def main():
    c = McpClient()
    docs = []
    try:
        def _pn(p: Path) -> int:
            m = re.search(r"part (\d+) of", p.name)
            return int(m.group(1)) if m else 0
        files = sorted(PARTS_DIR.glob("*.md"), key=_pn)
        print(f"found {len(files)} part files")
        for i, f in enumerate(files, 1):
            text = f.read_text(encoding="utf-8")
            cr = chapter_range(text)
            desc = (f"【Part {i}/26 · {cr or 'Gutenberg front/back matter'}】"
                    f"Pride and Prejudice (Jane Austen, PG#1342) 英文全文分块——"
                    f"{cr or 'front/back matter'} 的情节正文，用于长文本跨章检索。")
            r = c.call("kb_doc_create", {
                "kb_id": KB_ID, "name": f.name, "content": text,
                "description": desc, "tags": TAGS,
            }, timeout=180)
            ok = r.get("success")
            doc = (r.get("document") or {})
            path = doc.get("path") or doc.get("docPath") or ""
            docs.append({"part": i, "file": f.name, "ok": ok, "path": path,
                         "chars": len(text), "chapter_range": cr,
                         "raw": {k: v for k, v in r.items() if k != "document"}})
            print(f"[{i:2d}/26] ok={ok} path={path!r} chars={len(text)} {cr}")
        (OUT / "upload_result.json").write_text(
            json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nuploaded ok={sum(1 for d in docs if d['ok'])}/{len(docs)}")
    finally:
        c.close()


if __name__ == "__main__":
    main()
