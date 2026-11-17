elsarticle
stfloats
fontenc
inputenc
booktabs
array
graphicx
amsmath
amssymb
xcolor
url
hyperref
xurl
same
same
caption
font=small,labelfont=bf
algorithm
algpseudocode
--
figs/
1.5em
0.90
0.85
0.08
0.75
0.90
0.75
topnumber3
bottomnumber2
totalnumber4
dbltopnumber3
7pt plus 2pt minus 2pt
9pt plus 2pt minus 2pt
7pt plus 2pt minus 2pt
7pt plus 2pt minus 2pt
9pt plus 2pt minus 2pt
Knowledge-Based Systems
document
frontmatter
HMRS: A hierarchical management-and-retrieval system for tiered
knowledge document organisation and evidence-traced access
Author Namecor1
author@example.com
Co-author Name
Corresponding author.
organization=Affiliation Department, University,
City, Country, city=City, country=Country
abstract
Using document collections as a knowledge base requires parsing, placement,
maintenance and retrieval to work together. We present HMRS (Hierarchical
Management Retrieval System), a self-hosted knowledge document management
system managing documents at three levels---collection, document and
segment---and serving queries along a tiered path from the catalogue of
collections, through document descriptions, to the evidence-carrying segment.
Classification derives from the parsed body rather than the filename, with
descriptions exposed before any body is read. At the segment tier, an
optional gate admits evidence, and enforced checks stay separate from
workflow decisions.
On a 100-paper snapshot, 79 papers were retrievable and 21 not; cross-lingual
membership was 0.875 (EN) and 1.0 (ZH/JA). A 72-question scripted route audit
returned the gold collection for 72/72 with full route cards versus 37/72
with name-only cards; an unlogged fallback may use descriptions. On the same
questions, the tiered path with a chunk-window evidence union contained the
gold string in 52/72 (72.2\%), above a flat union with a reference-mode judge
(39/72) and a navigation-free precise arm (46/72; difference not statistically
resolved). The configurations differ
in multiple components, and a gold-label-dependent lookup limits the flat
comparison. A gold identifier appeared in all 60 answer-or-trace cells, and
verifier-score re-ranking lowered Hit@5 from 0.94 to 0.44 while
fusion order restored 0.94. These results demonstrate an auditable management
structure with per-tier measurements and warn against verifier-as-ranker;
they do not establish general retrieval superiority or semantic answer
quality, but position a managed, auditable collection as an inspectable basis
for evidence-traced knowledge bases.
abstract
keyword
Knowledge document management Document classification 
Hierarchical organisation Tiered retrieval Evidence verification 
Model Context Protocol
keyword
frontmatter
n1_intro
n2_related
n3_overview
n4_acquisition
n5_organization
n6_retrieval
n7_implementation
n8a_eval
n8b_eval
n8c_eval
n9_discussion
n10_threats
n11_conclusion
n_back
8pt9.5pt
0.3pt plus 0.1ex
8.6pt
same
elsarticle-num
refs,refs_new_verified
document