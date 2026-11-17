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