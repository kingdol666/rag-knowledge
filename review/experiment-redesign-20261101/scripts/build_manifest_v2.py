# -*- coding: utf-8 -*-
"""manifest v2 —— 数据驱动版：手写金标（v1 GOLD）+ corpus_spec_final 的锚金标（脚本实测命中才收）。

金标锚纪律不变：anchor 必须在文档文本中实测存在；缺失→该题丢弃并记录（防编造）。
运行: python build_manifest_v2.py
"""
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"

# v1 手写金标（既有 20 题，文件未变动，全部保留）
sys.path.insert(0, str(BASE))
from build_manifest import GOLD  # noqa: E402


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spec = json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))
    docs, golds, dropped = [], [], []
    seen_files = set()

    def file_text(rel):
        p = CORPUS / rel
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8", errors="replace")

    # 1) 手写金标
    for g in GOLD:
        t = file_text(g["doc"])
        if t is None:
            dropped.append((g["id"], "doc missing")); continue
        hit = None if g.get("evidence_pending") else (g["evidence_substr"] in t)
        if hit is False:
            dropped.append((g["id"], "evidence not found")); continue
        golds.append(dict(id=g["id"], domain=g["domain"], kind="gold",
                          question=g["question"], gold_doc=g["doc"],
                          gold_evidence=g["evidence_substr"],
                          evidence_pending=g.get("evidence_pending")))

    # 2) 锚金标（来自 spec；锚实测存在才收）
    auto_n = 0
    for m in spec:
        for d in m["docs"]:
            if d["file"] in seen_files:
                continue
            seen_files.add(d["file"])
            t = file_text(d["file"])
            b = (CORPUS / d["file"])
            docs.append(dict(path=d["file"], domain=m["slug"],
                             bytes=b.stat().st_size if b.exists() else 0,
                             sha256_head=hashlib.sha256(b.read_bytes()[:65536]).hexdigest()[:16]
                             if b.exists() else ""))
            if not d.get("anchor") or not d.get("question") or t is None:
                continue
            if d["file"].lower().endswith(".pdf"):
                # PDF 二进制：锚在解析入库后由判卷链验证（与手写 PDF 金标同口径）
                auto_n += 1
                golds.append(dict(id=f"A-{m['slug']}-{d['name'][:24]}", domain=m["slug"],
                                  kind="gold", question=d["question"], gold_doc=d["file"],
                                  gold_evidence=d["anchor"], evidence_pending="pdf-parse"))
                continue
            if d["anchor"].lower() in t.lower():
                auto_n += 1
                golds.append(dict(id=f"A-{m['slug']}-{d['name'][:24]}", domain=m["slug"],
                                  kind="gold", question=d["question"], gold_doc=d["file"],
                                  gold_evidence=d["anchor"], anchor_mode="title"))
            else:
                dropped.append((f"auto:{d['name']}", f"anchor missing: {d['anchor'][:30]}"))

    # 3) 拒答锚（沿用 s3 种子里的 4 条，生成 manifest 层记录）
    refusals = [
        dict(id="R1", kind="refusal", question="意大利面最佳煮制时间是多少分钟？", evidence_absent="al dente"),
        dict(id="R2", kind="refusal", question="量子计算机 Shor 算法的多项式时间分解复杂度是多少？", evidence_absent="Shor 算法"),
        dict(id="R3", kind="refusal", question="红军长征在遵义会议之前的行军路线经过了哪些省份？", evidence_absent="红军长征"),
        dict(id="R4", kind="refusal", question="川菜回锅肉的正宗做法需要哪几步？", evidence_absent="回锅肉"),
    ]

    per_domain = {}
    for g in golds:
        per_domain[g["domain"]] = per_domain.get(g["domain"], 0) + 1
    manifest = dict(
        name="multi-domain-complete-docs-20261101-v2-100plus",
        corpus_root=str(CORPUS),
        domains=len(spec), docs=len(docs),
        gold_questions=golds, refusals=refusals,
        per_domain_gold=per_domain,
        external=dict(qasper="external-datasets/qasper/（1585 篇完整论文 + 5049 QA + 证据段标注）"),
        dropped=dropped,
    )
    (ART / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(f"domains={len(spec)} docs={len(docs)} gold={len(golds)} (手写 {len([g for g in golds if not g['id'].startswith('A-')])} + 锚 {auto_n}) "
          f"dropped={len(dropped)}")
    print("per-domain gold:", json.dumps(per_domain, ensure_ascii=False))
    for fid, msg in dropped:
        print("  DROP:", fid, msg[:70])
    return 0


if __name__ == "__main__":
    sys.exit(main())
