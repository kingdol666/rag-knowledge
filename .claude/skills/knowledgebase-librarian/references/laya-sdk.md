# Laya Local Decision Engine

Laya is the local System One decision model used by the librarian filter when no engine is specified.

Official sources:

- Model: <https://huggingface.co/convaiinnovations/laya>
- SDK: <https://github.com/NandhaKishorM/laya>
- Documentation: <https://nandhakishorm.github.io/laya/>
- Package: <https://pypi.org/project/laya/>

## Install

```bash
python -m pip install laya
# optional local HTTP service
python -m pip install "laya[serve]"
```

Laya requires Python 3.10 or newer. The first model load may download a Hugging Face checkpoint. For a fully local/offline deployment, pre-cache the model and set `LAYA_LOCAL_ONLY=1`.

## Model selection

```text
LAYA_MODEL=convaiinnovations/laya
LAYA_SUBFOLDER=            # empty, multilingual, or typed-decisions
LAYA_LOCAL_ONLY=1          # optional; prevents Hugging Face network access
LAYA_THRESHOLD=0.5         # optional default filter threshold
```

The SDK call used by this skill is:

```python
import laya
agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
result = agent.predict(
    {"query": query, "text": candidate_text},
    {"evidence": {"type": "noul", "instructions": instruction}},
)
probability_true = result["answers"]["evidence"]["noul"]
```

`noul` is the probability of the positive/true answer in `[0, 1]`. The filter does not use `confidence` or `action.act_probability` as a substitute for `noul`. A compatible response may also expose `answers.evidence.probabilities.true`; that field is accepted only when `noul` is absent.

## Evidence question

For lookup questions the filter asks:

```text
Does the TEXT contain concrete evidence that directly helps answer the QUERY?
Answer yes only if a reader could quote or paraphrase a fact, number, name,
method, result, or event from the TEXT that the QUERY asks for. Topical similarity
alone is NOT enough.
```

For enumeration questions it asks whether the text contains at least one requested instance. Every candidate segment is evaluated independently. A segment is added to `result_list` only when `noul >= threshold`.

## Engine selection

```bash
# default: local Laya SDK
python scripts/jev_filter.py --engine laya --input candidates.json --require-real

# explicit remote Jev
python scripts/jev_filter.py --engine jev --input candidates.json --require-real
```

The two engines never silently fall back to one another. Laya results report `engine=laya`, `backend=laya_sdk`, `real_engine=true`, and `real_jev=false`. Jev results report `engine=jev`, `backend=http`, `real_engine=true`, and `real_jev=true`. Offline injected score functions are labelled `backend=offline` and do not count as a real engine.

Missing SDK/model, inference errors, missing scores, malformed scores, and out-of-range probabilities fail closed: the candidate is recorded with `kept=false` and no candidate enters `result_list`.
