#!/usr/bin/env python3
"""one-off patcher for 143 — v2: field-shelf map + spread packing + resume."""
from pathlib import Path
import ast

p = Path(__file__).resolve().parent.parent / "scripts" / "143_e2e_modes_baselines.py"
s = p.read_text(encoding="utf-8")

old = """    from chat_tracks import answer_closed_book
    from lib import McpClient

    def read_pack(out_path: Path, mode: str) -> str:
        d = json.loads(out_path.read_text(encoding="utf-8"))
        if mode == "C":
            return "\\n\\n".join(str(r.get("content") or "") for r in d.get("docs") or [])
        return str(d.get("evidence_pack") or "")
"""
new = """    from chat_tracks import answer_closed_book
    from lib import McpClient

    def field_shelf_map() -> dict:
        mapping = {}
        mc = McpClient()
        try:
            for k in (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []):
                kb_id = k.get("kb_id") or k.get("name")
                for d in (mc.call("kb_get_documents", {"kb_id": kb_id, "lightweight": True},
                                  timeout=120).get("catalog") or []):
                    name = str(d.get("name") or "")
                    if "__" in name:
                        f = name.split("__", 1)[0]
                        mapping.setdefault(f, {})
                        mapping[f][kb_id] = mapping[f].get(kb_id, 0) + 1
        finally:
            mc.close()
        return {f: max(kbs, key=kbs.get) for f, kbs in mapping.items()}

    fmap = field_shelf_map()
    print(f"[143] field-to-KB: {fmap}", flush=True)

    def spread_pack(docs, per_doc, budget):
        parts, total = [], 0
        for d in docs:
            if total >= budget:
                break
            piece = str(d.get("content") or "")[:per_doc]
            parts.append(piece)
            total += len(piece)
        return "\\n\\n".join(parts)[:budget]

    def mode_pack(out_path: Path, mode: str):
        d = json.loads(out_path.read_text(encoding="utf-8"))
        if mode == "C":
            docs = d.get("docs") or []
            return spread_pack(docs, 700, ANSWER_EVIDENCE_BUDGET), \
                [r.get("doc_path", "") for r in docs]
        if mode == "A":
            ordered = [{"doc_path": r.get("doc_path", ""),
                        "content": str(r.get("read_head") or "")}
                       for r in (d.get("result_list") or [])]
        else:
            ordered = [{"doc_path": s.get("doc_path", ""),
                        "content": str(s.get("text") or "")}
                       for s in (d.get("survivors") or [])]
        mc = McpClient()
        seen, docs = set(), []
        try:
            cat = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
            kb_of = {}
            for k in cat:
                kb_id = k.get("kb_id") or k.get("name")
                kb_of[str(k.get("name") or "").lower()] = kb_id
                kb_of[str(k.get("kb_id") or "").lower()] = kb_id
            for od in ordered:
                path = str(od.get("doc_path", "")).replace("\\\\", "/")
                key = path.lower()
                if not path or key in seen:
                    continue
                seen.add(key)
                kb_name = path.split("/")[0]
                kb_id = kb_of.get(kb_name.lower()) or kb_name
                r = mc.call("kb_doc_read", {"kb_id": kb_id,
                                            "doc_path": path.split("/", 1)[-1],
                                            "max_chars": 700}, timeout=120)
                docs.append({"doc_path": path,
                             "content": od.get("content") or str(r.get("content") or "")})
        finally:
            mc.close()
        return spread_pack(docs, 700, ANSWER_EVIDENCE_BUDGET), [d0["doc_path"] for d0 in docs]
"""
assert old in s, "block1 not found"
s = s.replace(old, new)

old2 = """            t0 = time.time()
            qd = {"text": q["question"], "shelf_b": [], "gold_substr": "", "gold_name": ""}
            out_path = run_dir / f"arm_{m}-{q['qid']}.json"
            print(f"[143] mode {m} \\u00d7 {q['qid']} retrieving \\u2026", flush=True)
            try:
                RUNNERS[m](qd, out_path)
                d = json.loads(out_path.read_text(encoding="utf-8"))
                kept = sorted({str(r.get("doc_path", "")).replace("\\\\", "/")
                               for r in (d.get("docs") or [])
                               }) if m == "C" else sorted(set(
                                   str(x).replace("\\\\", "/") for x in (d.get("kept_doc_paths") or [])))
                if m == "C":
                    kept = sorted({r.get("doc_path", "") for r in (d.get("docs") or [])})
                pack = read_pack(out_path, m)[:ANSWER_EVIDENCE_BUDGET]"""
new2 = """            t0 = time.time()
            field = str(q.get("field") or "")
            shelf = [fmap[field]] if field in fmap else []
            qd = {"text": q["question"], "shelf_b": shelf, "gold_substr": "", "gold_name": ""}
            out_path = run_dir / f"arm_{m}-{q['qid']}.json"
            if not out_path.exists():
                print(f"[143] mode {m} \\u00d7 {q['qid']} retrieving \\u2026", flush=True)
                RUNNERS[m](qd, out_path)
            try:
                pack, kept = mode_pack(out_path, m)
                pack = pack[:ANSWER_EVIDENCE_BUDGET]"""
assert old2 in s, "block2 not found"
s = s.replace(old2, new2)

old3 = """                ans = answer_closed_book(q["question"], pack)
                lat = round(time.time() - t0, 1)"""
new3 = """                ans = answer_closed_book(q["question"], pack)
                d = json.loads(out_path.read_text(encoding="utf-8"))
                lat = round(time.time() - t0, 1)"""
assert old3 in s, "block3 not found"
s = s.replace(old3, new3)

old4 = '''                       "ranked": kept,'''
assert old4 in s
p.write_text(s, encoding="utf-8", newline="\n")
ast.parse(s)
print("143 v2 patched OK")
