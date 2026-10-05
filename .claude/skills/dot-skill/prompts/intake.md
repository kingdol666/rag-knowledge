# Basic Info Intake Script

## Opening

```
I'll help you create this colleague's Skill. Just answer 3 questions — you can skip any of them.
```

---

## Question Sequence

### Q1: Alias / Codename

```
What should we call this colleague? (An alias, nickname, or codename all work; join multi-word names with -)

Example: qing-yun
```

- Accept any string
- Generated slugs always use `-` as the separator (never underscores)
- Chinese names are auto-converted to pinyin and joined with `-` ("青云" → `qing-yun`, "小李" → `xiao-li`)
- English names are lowercased and joined with `-` ("Big Mike" → `big-mike`)

---

### Q2: Basic Info

Bundle company, level, role, and gender into a single question so the user can answer in one sentence:

```
Describe their basic info in one sentence — company, level, role, gender. Write whatever comes to mind; skipping is fine.

Example: ByteDance 2-1 backend engineer male (字节 2-1 后端工程师 男)
```

Parse the following fields from the user's answer (leave missing ones empty):
- **Company**
- **Level**
- **Role**
- **Gender**

#### Job-Level Reference Table

| Company | Level format | Engineer/Researcher | Senior Engineer | Senior/Expert | Staff/Principal |
|---------|--------------|---------------------|-----------------|---------------|-----------------|
| ByteDance | X-Y | 2-1, 2-2 | 3-1, 3-2 | 3-3 | 3-3+ (O level) |
| Alibaba | P-level | P5, P6 | P7 | P8 | P9+ |
| Tencent | T-level | T1-1~T2-2 | T3-1, T3-2 | T4 | T4+ |
| Baidu | T-level | T5, T6 | T7 | T8 | T9+ |
| Meituan | P-level | P4, P5 | P6 | P7 | P8+ |
| Huawei | Numeric | 13-15 | 16-17 | 18-19 | 20-21 |
| NetEase | P-level | P1-P3 | P4 | P5 | P6+ |
| JD | T-level | T3-T4 | T5 | T6 | T7+ |
| Xiaomi | Numeric | 1-3 | 4-5 | 6-7 | 8+ |

**Rough cross-company equivalents**:

```
ByteDance 2-1/2-2  ≈  Alibaba P6   ≈  Tencent T2    ≈  Baidu T6
ByteDance 3-1      ≈  Alibaba P7   ≈  Tencent T3-1  ≈  Baidu T7
ByteDance 3-2      ≈  Alibaba P7+  ≈  Tencent T3-2
ByteDance 3-3      ≈  Alibaba P8   ≈  Tencent T4
```

> Note: ByteDance 2-1 is the engineer title; 3-1 and above are senior engineer.
> 2-1 roughly equals Alibaba P6 — the level of an independent engineer who owns complete tasks.

---

### Q3: Personality Profile

Bundle MBTI, zodiac, personality tags, corporate-culture tags, and subjective impressions into one free-form question:

```
Describe their personality in one sentence — MBTI, zodiac, personality traits, corporate-culture imprint, your impressions of them. Write whatever comes to mind; skipping is fine.

Example: INTJ Capricorn blame-shifter ByteDance-style, strict in CR but never explains why (INTJ 摩羯座 甩锅高手 字节范 CR很严格但从来不解释原因)
```

Identify and extract the following fields from the user's answer (leave missing ones empty):
- **MBTI**: one of the 16 standard types
- **Zodiac**: one of the 12 signs
- **Personality tags**: match against the tag library below; free-form descriptions are also accepted
- **Corporate-culture tags**: match against the tag library below
- **Subjective impressions**: free-form descriptions that fit no category — keep verbatim

#### Personality Tag Library

**Work attitude**: Conscientious (认真负责) / Good-enough (差不多就行) / Blame-shifter (甩锅高手) / Scapegoat (背锅侠) / Perfectionist (完美主义) / Procrastinator (拖延症)

**Communication style**: Direct (直接) / Beats around the bush (绕弯子) / Taciturn (话少) / Talkative (话多) / Loves voice messages (爱发语音) / Reads but never replies (只读不回) / Reads and replies nonsense (已读乱回) / Instant-reply compulsion (秒回强迫症)

**Decision style**: Decisive (果断) / Flip-flopper (反复横跳) / Relies on superiors (依赖上级) / Forceful pusher (强势推进) / Data-driven (数据驱动) / Pure gut feel (全凭感觉)

**Emotional style**: Emotionally stable (情绪稳定) / Thin-skinned (玻璃心) / Easily agitated (容易激动) / Cold and distant (冷漠疏离) / Pleasant on the surface (表面和气) / Passive-aggressive (阴阳怪气)

**Rhetoric and tactics**: PUA master (PUA 高手) / Office-politics player (职场政治玩家) / Blame-shifting artist (甩锅艺术家) / Upward-management expert (向上管理专家) / Loves to lecture (爱讲大道理) / Emotional blackmailer (情绪勒索)

#### Corporate-Culture Tag Library

- **ByteStyle (字节范)** — candid and direct, chases impact, opens with context, loves the word "align"
- **Alibaba flavor (阿里味)** — Six-Vein values (六脉神剑) vocabulary, loves jargon like "empower" (赋能), "grip" (抓手), "ecosystem" (生态), "closed loop" (闭环)
- **Tencent flavor (腾讯味)** — lets data speak, horse-racing mechanism, restrained and conservative, focused on user experience
- **Huawei flavor (华为味)** — striver culture, process-driven, loves PPT reporting, emphasizes execution
- **Baidu flavor (百度味)** — technology above all, strong hierarchy awareness, fierce internal competition
- **Meituan flavor (美团味)** — extreme execution, detail-obsessed, localization mindset
- **First principles (第一性原理)** — Musk-style: question the essence, reject reasoning by analogy, radical simplification
- **OKR zealot (OKR 狂热者)** — asks for the Objective first on everything, nitpicks every KR
- **Big-tech assembly line (大厂流水线)** — well-standardized but low creativity, SOP-dependent, afraid of taking the blame
- **Startup school (创业公司派)** — limited resources, full-stack thinking, results-oriented, tolerates chaos

---

## Confirmation Summary

After collection, show:

```
Summary:

  👤  {alias}
  🏢  {company} {level} {role} (omit if unfilled)
  ⚧   {gender} (omit if unfilled)
  🧠  {MBTI} {zodiac} (omit if unfilled)
  🏷️   Personality: {tag list} (omit if unfilled)
  🏢  Corporate culture: {tag list} (omit if unfilled)
  💬  Impressions: {impression text} (omit if unfilled)

All correct? (confirm / revise [field name])
```

After the user confirms, proceed to Step 2 file import.
