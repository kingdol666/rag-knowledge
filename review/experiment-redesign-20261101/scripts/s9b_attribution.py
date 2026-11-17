# -*- coding: utf-8 -*-
"""优化轮归因分析（s9b）：对 final_bench A0 的每个 gold 未命中 qid 定根因。

四类（按任务口径）：
  (a) routing-miss          —— gold_evidence 在路由 KB 的卷文件里找不到（含跨库在别处找到）
  (b) window-truncation-miss —— 在路由 KB 中找到，但落在参考模式抓取窗外
                                （char offset >40000，或行号 >200 —— 参考 fetch
                                kb_doc_read(max_chars=40000, limit=默认200行)）
  (c) judge-miss            —— 在窗内（前 40000 字符且 ≤200 行）却没进旧证据包
                                （候选未进 top-6 / 判卷段未存活）
  (d) format-mismatch       —— 精确子串不中，但大小写/空白归一化后命中（报告 normalized-hit）

用法: python s9b_attribution.py [--traces <s4_traces_final.json>] [--out <dir>]
输出: attribution_a0_misses.json + attribution_a0_misses.md（qid→类→offset 表）
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
EXP = BASE.parent
ART = EXP / "artifacts"
REPO = EXP.parents[1]
STORAGE = REPO / "storage" / "tree-file-system"


def norm(s: str) -> str:
    """归一化：casefold + 全部空白（含全角空格）折叠为空。"""
    return re.sub(r"[\s\u3000]+", "", str(s or "").casefold())


def find_in_kb(kb_folder: Path, needle: str, n_needle: str):
    """在 KB 卷目录逐文件找 needle；返回 (file, char_offset, line_no, kind) 或 None。
    优先精确匹配；无则归一化匹配（用弹性空白正则定位真实偏移）。"""
    if not kb_folder.exists():
        return None
    flex = re.compile(r"[\s\u3000]*".join(re.escape(ch) for ch in n_needle))
    exact_hits, norm_hits = [], []
    for fp in sorted(kb_folder.rglob("*.md")) + sorted(kb_folder.rglob("*.txt")):
        try:
            txt = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        idx = txt.find(needle)
        if idx >= 0:
            exact_hits.append((fp, idx))
            continue
        m = flex.search(txt)
        if m:
            norm_hits.append((fp, m.start()))
    if exact_hits:
        fp, idx = exact_hits[0]
        return fp, idx, None, "exact"
    if norm_hits:
        fp, idx = norm_hits[0]
        return fp, idx, None, "normalized"
    return None


def line_of(fp: Path, idx: int) -> int:
    try:
        return fp.read_text(encoding="utf-8", errors="replace")[:idx].count("\n") + 1
    except OSError:
        return -1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default=str(ART / "final_bench" / "s4_traces_final.json"))
    ap.add_argument("--out", default=str(EXP / "artifacts" / "opt_bench"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    traces = json.loads(Path(args.traces).read_text(encoding="utf-8"))
    a0 = traces["A0"]
    questions = {q["id"]: q for q in
                 (json.loads(l) for l in (ART / "provenance" / "questions.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip())}
    spec = json.loads((ART / "provenance" / "corpus_spec_final.json").read_text(encoding="utf-8"))
    kb_folder_of_slug = {m["slug"]: m["kb_name"] for m in spec}
    all_md_kbs = [p for p in STORAGE.iterdir()
                  if p.is_dir() and p.name.startswith("MD语料-")]

    misses = [r for r in a0 if not r.get("gold_hit") and not r.get("is_refusal")]
    print(f"A0 misses: {len(misses)}")
    rows = []
    counts = {"routing-miss": 0, "window-truncation-miss": 0,
              "judge-miss": 0, "format-mismatch": 0, "not-found-on-disk": 0}
    for tr in misses:
        qid = tr["qid"]
        q = questions.get(qid) or {}
        gold = q.get("gold_evidence") or ""
        ngold = norm(gold)
        route = tr.get("route_slug") or ""
        routed_kb = STORAGE / kb_folder_of_slug.get(route, "")
        hit = find_in_kb(routed_kb, gold, ngold) if routed_kb.exists() else None
        row = dict(qid=qid, route_slug=route, gold_doc=q.get("gold_doc"),
                   gold_evidence=gold[:60], char_offset=None, line_no=None,
                   volume="", gold_doc_in_survivors=None, top1=tr.get("top1"))
        if hit:
            fp, idx, _, kind = hit
            row.update(volume=str(fp.relative_to(STORAGE)).replace("\\", "/"),
                       char_offset=idx, line_no=line_of(fp, idx))
            if kind == "normalized":
                row["cls"] = "format-mismatch"
                row["normalized_hit"] = True
            else:
                # 旧参考抓取窗：min(前 200 行, 40000 字符)
                try:
                    txt = fp.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    txt = ""
                old_window = "\n".join(txt.splitlines()[:200])[:40000]
                if idx > 40000:
                    row["cls"] = "window-truncation-miss"
                    row["window_cut"] = "char_offset>40000"
                elif row["line_no"] > 200:
                    row["cls"] = "window-truncation-miss"
                    row["window_cut"] = "line>200_limit"
                elif gold in old_window:
                    row["cls"] = "judge-miss"
                    row["window_cut"] = None
                else:
                    row["cls"] = "window-truncation-miss"
                    row["window_cut"] = "chars+lines combined cut"
                # 旧 trace survivors 即 doc_path（KB/卷.md）——与归因到的卷文件精确对上
                row["gold_doc_in_survivors"] = row["volume"] in {
                    str(sp).replace("\\", "/") for sp in (tr.get("survivors") or [])}
        else:
            # 跨库：其余 MD语料-* KB 里找（精确→归一化）
            cross = None
            for kb in all_md_kbs:
                if kb.name == routed_kb.name:
                    continue
                h2 = find_in_kb(kb, gold, ngold)
                if h2:
                    cross = (kb.name, h2[3], h2[1])
                    break
            if cross:
                row["cls"] = "routing-miss"
                row["found_in_kb"] = cross[0]
                row["match_kind"] = cross[1]
            else:
                row["cls"] = "not-found-on-disk"
                row["note"] = "gold_evidence 不在任何 MD语料-* 卷文件（精确+归一化）"
        counts[row["cls"]] = counts.get(row["cls"], 0) + 1
        rows.append(row)
        print(f"  {qid:38s} {row['cls']:26s} off={row['char_offset']} "
              f"line={row['line_no']} vol={Path(row['volume']).name}")

    (out_dir / "attribution_a0_misses.json").write_text(
        json.dumps({"counts": counts, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # markdown 表
    lines = ["# A0 未命中归因（35 qids）", "",
             "| qid | class | routed KB | volume | char_offset | line | detail |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        detail = r.get("window_cut") or r.get("found_in_kb") or r.get("note") or ""
        if r.get("normalized_hit"):
            detail = "normalized-hit " + detail
        lines.append(f"| {r['qid']} | {r['cls']} | {r['route_slug']} | "
                     f"{Path(r['volume']).name or '-'} | {r['char_offset']} | "
                     f"{r['line_no']} | {detail} |")
    lines += ["", "## 计数", ""]
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    (out_dir / "attribution_a0_misses.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))
    print(f"wrote {out_dir/'attribution_a0_misses.json'} and .md")


if __name__ == "__main__":
    main()
