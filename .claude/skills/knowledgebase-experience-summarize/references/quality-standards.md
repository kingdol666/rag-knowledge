# Experience Quality Standards — The Gold Standard for Experience Quality

> An experience is not "writing down the conversation" — an experience is **reusable distilled practice**, abstract patterns extracted from concrete cases.
> At retrieval time, a low-quality experience is useless even when vectors hit it; a high-quality experience lets someone follow it and act.

## Table of Contents
- [Three Self-Check Questions](#three-self-check-questions)
- [Field Pass Criteria](#field-pass-criteria)
- [Bad Experiences vs Good Experiences](#bad-experiences-vs-good-experiences)
- [category Selection Guide](#category-selection-guide)
- [Dedup Rules](#dedup-rules)
- [Completeness Checklist](#completeness-checklist)

---

## Three Self-Check Questions

Before writing any experience, ask yourself:

1. **What real problem does this solve?** — When someone else hits the same scenario, can they immediately locate this experience?
2. **How actionable is it?** — After reading the solution, can someone follow it directly? Or does it just say "be careful"?
3. **What's missing?** — `problem` / `solution` / `key_lessons`: missing any one is unacceptable; a missing `related_docs` equals a broken link.

An experience ≠ a conversation log. An experience = **abstract patterns** distilled from concrete cases:
- ❌ "Today I searched for RAG material" (a diary entry)
- ✅ "For RAG retrieval, run two_stage first and supplement with vector; recall improved by 40%" (reusable knowledge; original: "RAG 检索时，先用 two_stage 再用 vector 补全，召回率提升 40%")

---

## Field Pass Criteria

| Field | Pass criteria | Length | ❌ Fails |
|------|---------|------|----------|
| `title` | Contains scenario words + method words (e.g. "coal mill blockage early warning" 磨煤机堵管预警) | Short | "Experience 1" (经验1) / "fault handling" (故障处理) |
| `scenario` | kebab-case with a domain prefix | e.g. `vla-deployment-sim2real` | `test` / no prefix |
| `problem` | A reproducible scenario, concrete down to times/quantities/conditions | ≥50 chars | "the equipment isn't working well" (设备不太好用) |
| `solution` | Has tools/methods/steps/configs/commands | ≥100 chars | "we checked it" (我们检查了一下) |
| `key_lessons` | Each entry independently citable, from different angles | Each ≥30 chars, 3-5 entries | "mind safety" (注意安全) / only 2 entries |
| `tags` | Domain word + method word + scenario word | ≥2 tags | Empty / only 1 |
| `related_docs` | Paths really exist in the KB | Verify with `kb_doc_read` | Nonexistent / empty (unless a pure conversation experience) |
| `severity` | Real severity matching the category | — | A tip-level fault marked normal |
| `category` | Pick the best match (see table below) | — | Troubleshooting marked tip |

### `solution` Hard Length Thresholds

| category | solution minimum chars |
|----------|-------------------|
| troubleshooting | 80 |
| best_practice / workflow | 100 |
| optimization | 80 |
| lesson_learned | 60 |
| decision | 60 |
| tip | 40 |

---

## Bad Experiences vs Good Experiences

### ❌ Bad Experience (too vague; useless even when retrieval hits it)
```yaml
problem: "The equipment isn't working well"          # 原文: "设备不太好用"
solution: "We checked it and adjusted some parameters"   # 原文: "我们检查了一下，调整了参数"
key_lessons: ["Mind the maintenance"]                # 原文: "要注意维护"
```

### ✅ Good Experience (concrete, actionable, reusable)
```yaml
problem: "Coal mill blockage caused boiler shutdowns; each unclog takes 3 hours, averaging 2 per month"
        # 原文: "磨煤机堵管导致停炉，每次清堵耗时3小时，月均2次"
solution: |
  Build a CNN-LSTM early-warning model:
  1. Extract three parameters from DCS historical data: mill current, inlet/outlet differential pressure, primary air flow
     (原文: "从 DCS 历史数据提取磨煤机电流、进出口差压、一次风量三参数")
  2. Train on sliding-window 60min samples labeled as blockage precursors
     (原文: "滑窗 60min 标注堵管前兆样本训练")
  3. Deploy real-time inference; trigger a warning above 0.8 probability
     (原文: "部署实时推理，超 0.8 概率触发预警")
  4. Human intervention within 315 minutes of the warning avoids the shutdown
     (原文: "预警后 315 分钟内人工介入可避免停炉")
key_lessons:
  - "Feature engineering uses all three: mill current + inlet/outlet differential pressure + primary air flow; none can be dropped"
    # 原文: "特征工程选磨煤机电流+进出口差压+一次风量三参数，缺一不可"
  - "At an 80% warning threshold: precision 95%, false-positive rate 3%; below 70%, false positives surge to 18%"
    # 原文: "预警阈值设80%时精度95%误报率3%，低于70%则误报激增至18%"
  - "A 60min sliding window is the optimal observation window for blockage precursors; 30min is noisy, 120min lags"
    # 原文: "滑窗60min是堵管前兆的最优观测窗口，30min噪声大、120min滞后"
```

→ Someone hitting the same scenario can apply it directly.

---

## category Selection Guide

| category | When to use | Key signals |
|----------|--------|---------|
| `troubleshooting` | Fault troubleshooting, error fixing | "报错" "失败" "排障" "修复" (error / failure / troubleshooting / fix) |
| `best_practice` | Verified best practices | "推荐" "标准做法" "最优" (recommended / standard practice / optimal) |
| `workflow` | Multi-step procedures / standard operating procedures | "步骤" "流程" "SOP" (steps / procedure / SOP) |
| `optimization` | Performance/efficiency optimization | "提升" "加速" "优化" "降本" (improve / speed up / optimize / cut costs) |
| `lesson_learned` | Lessons from failures/incidents | "教训" "事后" "回顾" (lesson / post-mortem / retrospective) |
| `decision` | Architecture/technology choice decisions and rationale | "选型" "决策" "为什么用X而非Y" (choice / decision / why X over Y) |
| `tip` | Small tricks/shortcuts (not systematic) | "技巧" "快捷" "小窍门" (trick / shortcut / knack) |

> Picking the wrong category misleads retrieval classification. Troubleshooting mis-tagged as tip → downweighted.

---

## Dedup Rules

A similar `scenario` already exists in the same KB → **do not create a new one**; take the update path ([crud-and-migration.md](crud-and-migration.md) §Update):

```
Check before creating:
  experience_search_global(kb_id, query="<scenario keywords>") → see whether it hits
  experience_list(kb_id, scenario="<same scenario>") → see whether it already exists

Hit → experience_update to add new lessons / update the solution
Miss → experience_create a new one
```

Same topic across KBs → each may exist (different KBs have different domain contexts), but `tags` should mark the related domains.

---

## Completeness Checklist

Go through item by item before create/update:

```
□ title contains scenario words + method words
□ scenario in kebab-case + domain prefix
□ problem ≥50 chars, concrete and reproducible
□ solution ≥ the threshold (see table above), with executable steps
□ key_lessons ≥3 entries, each ≥30 chars, independently citable
□ tags ≥2 (domain + method)
□ related_docs paths really exist (verify with kb_doc_read)
□ category matches the content
□ severity matches the category
□ same scenario not duplicated (dedup check)
```

Any item failing → fall back to drafting; do not force it into the library. An experience with missing fields is useless even when retrieval hits it.
