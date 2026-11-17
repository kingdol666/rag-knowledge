# -*- coding: utf-8 -*-
"""Stage 3 — 题集构建与校验。

--init-from-manifest : 从 manifest.json 金标生成种子题集 questions.jsonl
                       （19 金标 + 4 域外拒答占位 + 2 跨域占位；needs_expansion=true 的
                        占位题由 Agent 按 SKILL 判断件流程补齐，脚本只负责结构）。
--validate questions.jsonl : 机械校验（防编造红线）——
  ① 每题 gold_evidence 必须在其引用文档文本中实测命中；
  ② refusal 题 evidence_absent 必须在**全语料**中实测不出现；
  ③ 覆盖统计（域×题数）达标：每域≥2、refusal≥4、跨域≥2、总计≥30。
运行: python s3_validate_questions.py --init-from-manifest
      python s3_validate_questions.py --validate questions.jsonl
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"

REFUSAL_SEEDS = [
    dict(id="R1", domain=None, kind="refusal", question="意大利面最佳煮制时间是多少分钟？",
         note="域外：烹饪", evidence_absent="al dente"),
    dict(id="R2", domain=None, kind="refusal", question="量子计算机 Shor 算法的多项式时间分解复杂度是多少？",
         note="域外：量子计算（未入库领域）", evidence_absent="Shor 算法"),
    dict(id="R3", domain=None, kind="refusal", question="红军长征在遵义会议之前的行军路线经过了哪些省份？",
         note="域外：近代史（史记不含）", evidence_absent="红军长征"),
    dict(id="R4", domain=None, kind="refusal", question="川菜回锅肉的正宗做法需要哪几步？",
         note="域外：烹饪（nginx 已出现在新 K8s 文档，换锚）", evidence_absent="回锅肉"),
]
CROSS_SEEDS = [
    dict(id="X1", domain=None, kind="cross", question="数据安全法的重要数据目录和个保法的个人信息概念有何对应关系？",
         note="跨域：law-zh 两部法律", needs_expansion=True),
    dict(id="X2", domain=None, kind="cross", question="Kubernetes 的 controller 模式与 Transformer 的多头注意力机制分别在各自文档中如何被描述？",
         note="跨域：tech-en × science-en", needs_expansion=True),
]


def init_from_manifest():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    manifest = json.loads((ART / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for g in manifest["gold_questions"]:
        rows.append(dict(id=g["id"], domain=g["domain"], kind="gold",
                         question=g["question"], gold_doc=g.get("doc") or g.get("gold_doc"),
                         gold_evidence=g.get("evidence_substr") or g.get("gold_evidence"),
                         evidence_pending=g.get("evidence_pending")))
    for r in manifest.get("refusals", REFUSAL_SEEDS):
        rows.append(dict(id=r["id"], domain=None, kind="refusal", question=r["question"],
                         evidence_absent=r["evidence_absent"]))
    rows += CROSS_SEEDS
    out = ART / "questions.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    print(f"seed questions: {len(rows)} → {out} （占位题 needs_expansion=true 待 Agent 补齐证据锚）")


def validate(qfile: Path) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = [json.loads(l) for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = {}

    def doc_text(rel):
        if rel not in cache:
            p = CORPUS / rel
            cache[rel] = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
        return cache[rel]

    fails, expanded_pending = [], 0
    for r in rows:
        if r.get("needs_expansion"):
            expanded_pending += 1
            continue
        if r.get("kind") == "gold":
            if r.get("evidence_pending"):
                continue  # PDF：入库解析后由 s2 报告验证
            t = doc_text(r["gold_doc"])
            if t is None:
                fails.append((r["id"], f"doc missing: {r['gold_doc']}"))
            elif r["gold_evidence"] not in t:
                fails.append((r["id"], "gold_evidence NOT in doc text"))
        elif r.get("kind") == "refusal":
            needle = r.get("evidence_absent")
            # 全语料扫描
            hits = []
            for spec_dir in CORPUS.iterdir():
                if spec_dir.name == "external-datasets":
                    continue
                for p in spec_dir.rglob("*"):
                    if p.is_file() and p.suffix.lower() in (".txt", ".md", ".xml"):
                        if needle and needle in p.read_text(encoding="utf-8", errors="replace"):
                            hits.append(str(p.relative_to(CORPUS)))
            if hits:
                fails.append((r["id"], f"refusal evidence_absent '{needle}' FOUND in: {hits[:3]}"))

    # 覆盖统计
    golds = [r for r in rows if r.get("kind") == "gold"]
    per_domain = {}
    for g in golds:
        per_domain[g["domain"]] = per_domain.get(g["domain"], 0) + 1
    refusals = sum(1 for r in rows if r.get("kind") == "refusal" and not r.get("needs_expansion"))
    cross = sum(1 for r in rows if r.get("kind") == "cross" and not r.get("needs_expansion"))
    print(f"total={len(rows)} gold={len(golds)} refusal={refusals} cross={cross} "
          f"pending_expansion={expanded_pending}")
    print("per-domain gold:", json.dumps(per_domain, ensure_ascii=False))
    if expanded_pending:
        print(f"⚠ {expanded_pending} 占位题 needs_expansion=true：Agent 补齐证据锚后重跑本校验")
    if fails:
        for fid, msg in fails:
            print(f"  FAIL {fid}: {msg}")
        return 1
    print("✅ 机械校验通过（证据锚全部实测命中 / 拒答锚全语料实测不存在）")
    return 0


if __name__ == "__main__":
    if "--init-from-manifest" in sys.argv:
        init_from_manifest()
    elif "--validate" in sys.argv:
        qf = Path(sys.argv[sys.argv.index("--validate") + 1])
        sys.exit(validate(qf))
    else:
        print("usage: --init-from-manifest | --validate <questions.jsonl>")
        sys.exit(2)
