# Description Writing Guide (A4)

> **Core principle**: descriptions must be based on **real content you have read**, not filenames, sources, or guesses. Without reading the document, writing a description is blind — you might describe "RAG for AIGC" as "Corrective RAG" or "Generative Agents" as "MetaGPT." **You must read the content first, then generate the description from the content summary.**
>
> The foundation of Agentic-first retrieval is this: the Agent can determine whether a document/KB is relevant to a scenario **by reading only its description**. This requires descriptions to be derived from real content summaries.

---

## A4-0 — Golden Rule: Read First, Then Describe

**Every document entering the KB (including KB-level descriptions) must be read before a description is written:**

```
# Parse-path documents (parse first, then read, then describe)
parse_doc(...) → wait for completion → read first 3000 chars of markdown → generate description

# Direct-path documents (content already available)
kb_doc_read(kb_id, doc_path, max_chars=3000, offset=0)
→ AI analyzes content → generates description
```

**Prohibited:**
- Writing a description based only on the filename (filenames can be wrong!)
- Writing "Parsed from XXX.pdf" without reading content
- Copying an abstract from the source PDF (may not match what was actually ingested)
- Writing from memory or training data (stale or mismatched)

---

## A4-1 — Sub-Agent Content Summary Workflow

> When many documents are being ingested simultaneously, reading each one in the main context is expensive. This workflow delegates content extraction and description generation to a **sub-agent**; the main agent only dispatches and validates.

**When to use a sub-agent:**
- Single batch of >= 3 documents
- Single document > 50 KB (including parsed output)
- Document language the main agent is not proficient in (e.g., classical Chinese, German, specialized notation)

**Sub-agent invocation:**

```
Agent(
  subagent_type="general-purpose",
  prompt="""Read the first 2000 characters of this document, then output a structured content summary.

Document path: {file_path} (or markdown_path)
Source filename: {filename}

Output format (pure JSON, no markdown code block wrapping):
{
  "title": "Real document title (extracted from first 2000 characters)",
  "content_preview": "First 100 chars of real content summary",
  "domain": "Detected domain",
  "methods": ["method1", "method2"],
  "scenario": "Applicable scenario description (1-2 sentences)",
  "key_results": "Key findings or data (if any)",
  "language": "zh/en/bilingual",
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "suggested_description": "Full content-based description (A4 format)"
}"""
)
```

**Validation checks on sub-agent output:**
- Does the description contain specific method/equipment names? If not, reject.
- Does `content_preview` match real content? If clearly inconsistent, reject.
- Does extracted `title` align with what the filename suggests? If not, annotate with "Warning: filename may be incorrect."

---

## A4a — Document-Level Description Template

```
[Subject] + [Method/Technology] + [Problem solved / Applicable scenario] + [Key findings/Data] + [Language]
```

**Element breakdown:**

1. **Subject**: What equipment/system/domain (coal mill / steam turbine / CNN-LSTM / knowledge graph)
2. **Method**: What method is used (CNN-LSTM / MSET / mutual information / Bayesian network)
3. **Scenario**: What problem it solves (coal blockage warning / early fault diagnosis / performance degradation trend prediction)
4. **Data highlight**: Key results (315 min early warning / 96.7% accuracy / 660 MW field test)
5. **Language**: zh / en / bilingual

**Good examples:**
- "A CNN-LSTM-based coal mill blockage fault warning method for thermal power plants. Uses DCS historical data to train a multi-input single-step prediction model, enabling gradual fault early identification through real residual analysis. Field tested on a 660 MW unit, providing 315 min early warning with no false alarms. Applicable to mill gradual fault early warning and deviation threshold calibration. Chinese."
- "Wind turbine gearbox fault diagnosis practice summary. Covers characteristic frequency calculation and vibration/oil/temperature three-parameter cross-validation for 6 fault types: tooth pitting/wear, bearing inner ring/outer ring/cage/rolling element. Applicable to gearbox early fault troubleshooting and condition monitoring system parameter calibration. Chinese."

**Bad examples (ambiguous scenarios, not locatable):**
- "A paper about coal mills" (no method, no scenario, no highlight)
- "AI-based warning system" (no equipment, no specific scenario)
- "test" / "document" / "material" (completely uninformative)
- "Parsed from XXX.pdf" (no content information; Agent cannot judge relevance)

---

## A4b — KB-Level Description Template (Hierarchical)

**Parent KB** (broad coverage, helps the Agent decide on the high-level category):

```
[Industry/Domain] + [List of covered sub-domains] + [Method summary] + [Content type] + [Language]
```

- "Energy industry research repository covering thermal power plant auxiliary equipment diagnostics: coal mill fault prediction (CNN-LSTM/MSET), boiler tube leak detection, steam turbine vibration analysis, fan-and-pump condition monitoring. Methods include deep learning, signal processing, and statistical modeling. English and Chinese academic papers. For power plant equipment health management and intelligent early warning scenarios."

**Sub-KB** (focused precision, lets the Agent make exact matches):

```
[Specific equipment/Sub-domain] + [Core technology methods] + [Applicable scenario] + [Document count] + [Language]
```

- "Coal mill (pulverizer) fault prediction and early warning research. Covers CNN-LSTM, MSET, BP-SVR methods for coal choking, coal blockage, and grinding roller wear detection. Real 660 MW power plant data verified. For coal mill condition monitoring, early warning system configuration, and residual threshold tuning scenarios. 5 documents. Chinese."
- "Steam turbine and generator condition monitoring. Covers vibration analysis, exciter fault detection, and coupling misalignment diagnosis. For turbine-generator unit predictive maintenance and vibration trend analysis scenarios. 3 documents. English."

---

## A4c — Self-Check (Mandatory After Every Description)

Ask yourself: **"If someone in the future encounters [the scenario I described], would reading just this one-sentence description let them be 100% sure this document is what they need?"**

The answer must be "yes." Otherwise, rewrite.

**Self-check focus by abstraction layer:**
- Parent KB description -> helps the Agent decide "whether to enter this broad category"
- Sub-KB description -> helps the Agent decide "this is the exact match I need"
- Document description -> assists verification of the precise snippet

---

## A4d — Content Verification (Mandatory)

After writing the description into the KB, perform final verification:

```
# 1. Compare description claims against real content
kb_doc_read(kb_id, doc_path, max_chars=500)

# 2. Check whether key claims in the description appear in the real content
#    - If description says "CNN-LSTM method" -> content should contain CNN, LSTM
#    - If description says "315 min early warning" -> content should contain 315

# 3. If claims cannot be found in the content -> description may be guessed -> rewrite
```

**Auto-detection rules:**

```
if "CNN-LSTM" in description and "CNN-LSTM" NOT in content_first_500:
    Warning: "Description mentions CNN-LSTM but content doesn't. Revise."

if "accuracy 94.5%" in description and "94.5" NOT in content_first_500:
    Warning: "Description claims 94.5% accuracy but not found in content. Verify."
```
