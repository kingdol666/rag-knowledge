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
HMRS: A hierarchical management retrieval system for tiered knowledge
document organisation and evidence-traced access
Author Namecor1
author@example.com
Co-author Name
Corresponding author.
organization=Affiliation Department, University,
City, Country, city=City, country=Country
abstract
A document collection becomes a knowledge base only when its documents are
parsed, classified into the owning collection, kept consistent as it changes,
and searched there. We present HMRS (Hierarchical Management Retrieval
System), a self-hosted knowledge document management system managing
documents at three levels---collection, document and segment---and answers
along a tiered path narrowing from the catalogue of collections, through
document descriptions, to the segment carrying the evidence. Classification
at the collection level derives from the parsed body, not the filename. The
shelf tier exposes descriptions and tags before any body is read, and the
segment tier admits evidence under an optional gate. Enforced checks are separated
from workflow decisions. A 100-paper snapshot left 79 papers retrievable and
21 not, with incomplete failure attribution. Automatic collection membership
was 0.875 for English and 1.0 for Chinese and Japanese. In a 72-question route
audit, the collection-selection arm returned the gold collection for 72/72
and name-only for 37/72, though an unlogged fallback could use descriptions.
Exact-string containment was 37/72 and 33/72; a read-all script found them in
72/72 cases after 879 parts (24.3 MB, 253.7 s) without answering. Across two
ten-question answer grids, all 60 cells contain a gold identifier, while
lexical and citation-marker checks vary by substrate. Verifier-score
re-ranking lowers Hit@5 from 0.94 to 0.44 on a 16-question set; fusion order
restores 0.94, and the threshold rejects no score. These results show
selected implemented management paths and failure boundaries, not general
retrieval superiority, semantic answer quality or citation support.
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
7.2pt7.8pt
0pt plus 0.1ex
7.4pt
same
elsarticle-num
refs,refs_new_verified
document