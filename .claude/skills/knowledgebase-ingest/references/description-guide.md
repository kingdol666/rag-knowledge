# Description Writing Guide

> **Core principle**: descriptions must be based on **real content you have read**, not filenames or guesses.

## Golden Rule
Read first, then describe. Writing a description without reading the document is prohibited.

```
# Parse-path: parse → wait → read 3000 chars → describe
# Direct-path: read content → describe
```

## Document-Level Template
```
[Subject] + [Method/Technology] + [Problem solved / Scenario] + [Key findings/Data] + [Language]
```

**Good**: "A CNN-LSTM-based coal mill blockage fault warning method for thermal power plants. Uses DCS historical data to train a multi-input single-step prediction model, enabling gradual fault early identification through real residual analysis. Field tested on a 660 MW unit, providing 315 min early warning with no false alarms. Chinese."

**Bad**: "A paper about coal mills" / "Parsed from XXX.pdf" / "test"

## KB-Level Template (Hierarchical)
**Parent KB**: `[Industry/Domain] + [sub-domains covered] + [method summary] + [content type] + [language]`
**Sub-KB**: `[Specific equipment/Sub-domain] + [core methods] + [scenario] + [doc count] + [language]`

## Self-Check
"If someone encounters [the scenario I described], would reading just this one-sentence description let them be 100% sure this document is what they need?" → Must be "yes".

## Content Verification (Mandatory)
After writing description:
```
kb_doc_read(kb_id, doc_path, max_chars=500)
# Verify key claims in description appear in real content
# If "CNN-LSTM" in description but NOT in content → rewrite
```

## Sub-Agent Delegation (for ≥3 docs or >50KB)
Delegate to sub-agent with: content sample (2000 chars), filename, existing KB list, tag vocabulary. Request JSON: `title, domain, methods, scenario, key_results, language, suggested_tags, suggested_description`. Validate: description contains specific method/equipment names, content_preview matches real content.
