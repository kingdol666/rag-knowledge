# Platform Smoke Benchmark — rag-knowledge

Generated 2026-09-17 12:14 UTC · pipeline: `benchmark-suite/TEST-PLAN.md` · corpus: 50 real multi-field papers in `data/papers/`

Simple functional tests only: document parse/upload, content retrieval QA,
experience summarisation. No IR metrics, no LLM judge, no baseline
comparison — deterministic checks against the live platform.

## 1. Document parse & upload (official MinerU chain)

- Papers parsed & stored: **50/50** · catalog documents: 50 · batch-indexed: 50
- Per-paper vector probes: **all ok** · graph build: **True** · tags: 202 · wall time: 1115.5 s

## 2. Content retrieval QA (1 question per paper, deterministic)

- Pass rate: **47/50 (94%)** — gold document in top-3 AND keyword verified in retrieved content

| QID | Field | Doc hit | Keywords hit | Verdict |
|---|---|:---:|---|:---:|
| Q01 | artificial-intelligence | True | — | FAIL |
| Q02 | nlp | True | training, bidirectional, transformers, language | PASS |
| Q03 | large-language-models | True | language, models, learners | PASS |
| Q04 | quantum-physics | True | noisy intermediate-scale | PASS |
| Q05 | clinical-medicine | True | multimedqa, medqa | PASS |
| Q06 | genomics | True | molecular function, biological process, cellular component | PASS |
| Q07 | economics | True | unified growth theory | PASS |
| Q08 | climate-science | True | — | FAIL |
| Q09 | astronomy | True | methanol, multibeam, survey | PASS |
| Q10 | materials | True | oxygen, redox, battery, cathodes | PASS |
| Q11 | neuroscience | True | review, neural, network | PASS |
| Q12 | robotics | True | multilayer, perceptron, based, simultaneous | PASS |
| Q13 | artificial-intelligence | True | navigating, state, cognitive, context | PASS |
| Q14 | artificial-intelligence | True | propositional, logic, plausible, reasoning | PASS |
| Q15 | nlp | True | language, models, learn, facts | PASS |
| Q16 | nlp | True | mameloshnlm, yiddish, language, model | PASS |
| Q17 | large-language-models | True | vision, scaling, human, labeled | PASS |
| Q18 | large-language-models | True | demystifying, instruction, mixing, tuning | PASS |
| Q19 | quantum-physics | True | continuous, quantum, error, correction | PASS |
| Q20 | quantum-physics | True | entanglement, assisted, quantum, error | PASS |
| Q21 | clinical-medicine | True | clinical, utility, predictive, accuracy | PASS |
| Q22 | clinical-medicine | True | using, clinical, representations, improving | PASS |
| Q23 | genomics | True | spacetx, roadmap, benchmarking, spatial | PASS |
| Q24 | genomics | True | visualization, spatial, transcriptomic | PASS |
| Q25 | economics | True | inequality, mobility, financial, accumulation | PASS |
| Q26 | economics | True | infrastructure, investment, economic, growth | PASS |
| Q27 | climate-science | True | hamiltonian, distributed, chaos, asian | PASS |
| Q28 | climate-science | True | large, scale, features, southwest | PASS |
| Q29 | astronomy | True | energy, survey, processing, calibration | PASS |
| Q30 | materials | True | design, battery, materials, defects | PASS |
| Q31 | neuroscience | True | spiking, inception, module, multi | PASS |
| Q32 | robotics | True | multi, camera, framework, using | PASS |
| Q33 | chemistry | True | autonomous, reaction, network, exploration | PASS |
| Q34 | mathematics | True | tailored, presolve, techniques, branch | PASS |
| Q35 | gravitational-physics | True | moriond, proceedings, extension, frequency | PASS |
| Q36 | statistics | True | causal, inference, algebraic, geometry | PASS |
| Q37 | speech | True | supervised, speech, training | PASS |
| Q38 | power-systems | True | mapping, disruption, sources, power | PASS |
| Q39 | medical-imaging | True | introduction, medical, imaging, modalities | PASS |
| Q40 | immunology | True | strategies, tumor, elimination, control | PASS |
| Q41 | oceanography | True | approximate, deconvolution, large, simulation | PASS |
| Q42 | seismology | True | automated, event | PASS |
| Q43 | agriculture | True | agriculture, driving, expansion, neolithic | PASS |
| Q44 | finance | True | backtest, trading, systems, candle | PASS |
| Q45 | social-networks | True | information, consumption, boundary, spanning | PASS |
| Q46 | databases | True | online, sketch, based, query | PASS |
| Q47 | chemistry | False | theory, laser, catalysis, pulses | FAIL |
| Q48 | mathematics | True | optimal, distributed, control, stochastic | PASS |
| Q49 | speech | True | reinforcement, learning, based, speech | PASS |
| Q50 | databases | True | bitvector, aware, query, optimization | PASS |

## 3. Experience summarisation (deterministic smoke)

- Extractor candidates: 13 · drafts created: 13 · library size: 1
- Create + search round-trip: **PASS** (created experience found by search: True)

## Verdict

- ✅ parse/upload
- ✅ index probes
- ✅ retrieval QA >= 90%
- ✅ experience round-trip

**Overall: PASS**
