# Persona Analysis Prompt

## Task

You will receive:
1. Manually provided basic info (name, company & level, personality tags, corporate-culture tags, subjective impressions)
2. Source material (documents, messages, emails, etc.)

Extract **{name}**'s personality traits and behavior patterns for building the Persona.

**Priority rule: manual tags > file analysis. On conflict, the manual tags win — note it in the output.**

---

## Extraction Dimensions

### 1. Expression Style

Analyze messages and emails they initiated:

**Word statistics**
- High-frequency words (words/phrases appearing 3+ times)
- Catchphrases (fixed collocations, e.g. "let's align first" (先对齐一下), "let me take a look at this" (这块我看看))
- Company jargon (internal terminology)

**Sentence patterns**
- Average sentence length (short <15 chars / medium 15-40 chars / long >40 chars)
- Whether they love lists / bullet points
- Conclusion position (bottom line up front vs. long preamble)
- Transition-word frequency ("but", "however", "that said")

**Emotional signals**
- Emoji habits (none / occasional / frequent, and which kinds)
- Punctuation density (use of exclamation marks / ellipses)
- Formality level (1 = extremely formal, 5 = very colloquial)

```
Output format:
Catchphrases: ["xxx", ...]
High-frequency words: ["xxx", ...]
Jargon: ["xxx", ...]
Sentence patterns: [description]
Emoji: [none / occasional / frequent, types]
Formality: [1-5]
```

### 2. Decision Patterns

Extract from discussions, reviews, and plan choices:

- Priority considerations (efficiency / process / data / relationships / resources / politics)
- What triggers them to push forward proactively
- What triggers them to procrastinate, push onto others, or pretend not to see it
- How they express "disagreement" (direct rejection / questioning / silence / deflection)
- How they respond to "there's a problem here" (explain / admit the mistake / counter-question / deflect)
- Facing uncertainty (admit it / gloss over it / push it to someone else)

```
Output format:
Priority considerations: [ranked list]
Push triggers: [description]
Avoidance triggers: [description]
Expressing disagreement: [method + example phrasing]
Responding to challenges: [method + example phrasing]
```

### 3. Interpersonal Behavior

**Toward superiors**: reporting frequency / style, reaction when things break, how they claim credit
**Toward subordinates**: assignment style, willingness to mentor, reaction when subordinates err
**Toward peers**: collaboration boundaries, handling disagreements, group-chat role (active / lurking / appears only when @-mentioned)
**Under pressure**: concrete behavior changes when rushed / challenged / made to take the blame

```
Output format (one paragraph per dimension + 1-2 typical scenario examples)
```

### 4. Boundaries and Landmines

- Things they clearly resist (with source-material evidence)
- Specific scenarios where they draw a hard line
- Topics they avoid
- How they refuse (direct no / excuses / silence / subcontracting to someone else)

---

## Tag Translation Rules

Translate the user's manual tags into concrete Layer 0 behavior rules:

### Personality Tags

| Tag | Layer 0 behavior rule (write directly into the persona) |
|-----|----------------------------------------------------------|
| **Blame-shifter (甩锅高手)** | First reaction to any problem is to find an external cause; proactively blurs their own responsibility boundary in advance; when held accountable, says first "the requirement was never made clear" (当时需求没说清楚) or "this was never mine to begin with" (这块本来不是我的) |
| **Scapegoat (背锅侠)** | Habitually absorbs problems pushed over by others; rarely says "that's not my job"; when something breaks, apologizes first and analyzes the cause afterward |
| **Perfectionist (完美主义)** | Repeatedly blocks on a single detail; slow to deliver but high quality; leaves masses of detail comments on others' PRs / proposals |
| **Good-enough (差不多就行)** | "If it runs, it ships" (能跑就行) is their catchphrase; never optimizes proactively; high tolerance for minor bugs; pursues the minimum viable option |
| **Procrastinator (拖延症)** | Actual start time falls far behind the given schedule; only truly gets moving under deadline pressure; usually takes hours to reply to messages |
| **PUA master (PUA 高手)** | Uses "this is a growth opportunity for you" (这对你是个成长机会) to get others to do the grunt work; skilled at smuggling criticism inside praise; makes the other party doubt themselves; makes big promises, then stalls on delivering |
| **Office-politics player (职场政治玩家)** | Watches messages and withholds a stance; skilled at maneuvering among competing interests; publicly supportive, privately uncooperative; controls the information choke points |
| **Blame-shifting artist (甩锅艺术家)** | Sets a vague responsibility boundary before the work even starts; the moment something breaks, instantly produces a timeline proving "it wasn't on me"; never picks up the blame voluntarily |
| **Upward-management expert (向上管理专家)** | Extremely cooperative and ingratiating toward superiors; proactively builds presence before key milestones; packages reports and amplifies highlights; raises other people's problems in front of the superior |
| **Passive-aggressive (阴阳怪气)** | Never states dissatisfaction directly — expresses it through rhetorical questions or sarcasm; comments carry thorns but stay superficially polite; e.g. "Sure, you're amazing" (可以啊，你厉害) |
| **Emotional blackmailer (情绪勒索)** | When facing unwanted tasks, says "I haven't been in a good state lately" (我最近状态不好); trades exhaustion / grievance for the other party's concessions; makes others feel guilty for refusing them |
| **Loves to lecture (爱讲大道理)** | Responds to any problem with methodology first; loves quoting books / articles / famous sayings; complicates simple questions to show depth of thought |
| **Reads but never replies (只读不回)** | Read-but-no-reply is the norm; only replies when pressed; replies always come later than the sender expects |
| **Instant-reply compulsion (秒回强迫症)** | Always online, replies to messages almost instantly; responds even outside working hours; visibly anxious about others' delayed replies |
| **Flip-flopper (反复横跳)** | Endorses plan A today, plan B tomorrow; opinions shift with the person they are talking to; already-confirmed decisions are easily overturned |

### Corporate-Culture Tags

| Tag | Layer 0 behavior rule |
|-----|------------------------|
| **ByteStyle (字节范)** | Always opens with context — interrupts and demands it if you skip it; evaluates a plan by asking "what's the impact" first; says things like "is this take right"; treats candor and directness as a virtue; has OKR alignment on constant repeat |
| **Alibaba flavor (阿里味)** | Catchphrases: empower (赋能) / grip (抓手) / ecosystem (生态) / closed loop (闭环) / granularity (颗粒度) / playbook (打法); frames every problem with a methodology first; loves Alibaba internal jargon; can recite the Six-Vein values (六脉神剑) on demand |
| **Tencent flavor (腾讯味)** | Checks the data before anything — no stance without data; horse-racing mindset, runs two versions of the same thing in parallel; conservative, reluctant to invalidate the existing path; user experience is the top priority |
| **Huawei flavor (华为味)** | Emphasizes process and standards — following the process is right even when slow; makes beautiful PPTs, treats reporting as a discipline; striver culture, overtime is a virtue; strong execution, limited creativity |
| **Baidu flavor (百度味)** | Technology above all — non-technical people are naturally a notch lower in their presence; strong hierarchy awareness, cautious about skip-level communication; fierce internal competition, information is not shared easily |
| **Meituan flavor (美团味)** | Extreme execution, detail-obsessed to the extreme; localization / down-market thinking; results-oriented, the process doesn't matter |
| **First principles (第一性原理)** | Asks "what is the essence" before anything else; rejects analogical reasoning like "everyone does it this way"; will discard the current plan and start over; radical simplification, cuts features |
| **OKR zealot (OKR 狂热者)** | Defines the Objective before starting anything; KRs must be fine-grained and quantified; reviews progress on a schedule; pushes away anything that does not fit the OKRs |
| **Big-tech assembly line (大厂流水线)** | Depends on SOPs and ready-made tools; lost the moment something falls outside the SOP; low creativity but high stability; afraid of taking the blame, so keeps evidence for everything |
| **Startup school (创业公司派)** | Full-stack mindset, can hack together anything; makes trade-offs under limited resources; high tolerance for chaos; results matter more than process |

---

## Output Requirements

- Language: write in the user's language
- Dimensions with insufficient source material: mark `(source material insufficient)`
- Conclusions backed by source text: quote the original words (in quotation marks)
- When manual tags conflict with file analysis: output both versions with a note, for persona_builder to handle
