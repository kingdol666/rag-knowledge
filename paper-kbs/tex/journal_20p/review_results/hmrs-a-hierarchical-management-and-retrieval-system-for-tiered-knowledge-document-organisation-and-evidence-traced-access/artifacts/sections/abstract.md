abstract
Document collections support knowledge work only when acquisition,
organisation, maintenance and access are connected. We present HMRS, a
self-hosted system that manages collections, documents and segments through
catalogue, shelf, document and segment views. Parsed content informs collection
assignment; document files, the tree registry and per-library metadata support
lifecycle audits. An optional evidence gate scores passages without
establishing entailment; pinned search may bypass catalogue navigation.
In a 100-paper arXiv campaign, 79 papers were retrievable and 21 were not; a
separate 400-page-per-language test measured 0.875 (English) and 1.0
(Chinese/Japanese) assignment accuracy. A scripted 72-question route audit
selected the gold collection in 72/72 full-card versus 37/72 name-only cases
(an unlogged fallback may use descriptions). On the same questions, frozen
annotated target-string containment in returned evidence packs was 52/72 for
the tiered chunk-window arm and 46/72 for the per-library union without
catalogue navigation (PD); the same-question follow-up gave 51/72 (70.8\%) and
45/72, with the arm ordering preserved in all three records, the difference
from PD unresolved, and a scoped flat union at 39/72. These are lexical
proxies (a sibling-document match may count), not gold-document retrieval or
semantic answer quality. Arms vary in multiple components; the flat lookup may
depend on the gold domain. Gold identifiers appeared in all 60 answer-or-trace
cells, which does not establish document reachability; document-style citation
markers separated the arms (9/10 versus 2/10), a lexical contrast. In a
same-pool replay of a retired hybrid wrapper, verifier re-ranking lowered
Hit@5 from 15/16 to 7/16, fusion order restored 15/16, and all 191 recorded
scores exceeded threshold.
The results document an auditable structure, not general retrieval superiority,
semantic answer quality or reliability; the replay warns against one historical
ordering configuration, and filtering was not tested on that pool.
abstract