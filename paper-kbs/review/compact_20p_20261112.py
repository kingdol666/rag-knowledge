"""One-time content compaction; preserves the extended positioning table as S11."""
from pathlib import Path
import re

src = Path(__file__).resolve().parents[1] / 'tex/journal_20p'
p = src / 'n1_intro.tex'
s = p.read_text(encoding='utf-8')
start = s.index('This paper presents HMRS')
end = s.index('The platform integrates', start)
s = s[:start] + r'''HMRS (Hierarchical Management Retrieval System) is a self-hosted
knowledge document management system. It maintains collections, documents and
segments and supports a catalogue--shelf--document--segment access path.
An ingest agent selects collections from parsed content, while lifecycle audits
compare relevant files and registries. The optional evidence gate scores
candidate segments; it does not prove support. Answer workflows distinguish a
completed search without evidence from tool failure. These stages are described
in Sections~\ref{sec:system}--\ref{sec:implementation}.

''' + s[end:]
p.write_text(s, encoding='utf-8')

p = src / 'n2_related.tex'
s = p.read_text(encoding='utf-8')
start = s.index('\\begin{table*}[t]')
end = s.index('\\end{table*}', start) + len('\\end{table*}')
table = s[start:end]
table = re.sub(r'\\citep?\{[^}]+\}', '', table)
table = table.replace('Section~\\ref{sec:eval}', 'the main paper')
table = table.replace('Sections~\\ref{sec:system}--\\ref{sec:lanes}', 'Main paper, Sections 3--7')
table = table.replace('Section~\\ref{sec:threats}', 'the main paper limitations')
table = table.replace('\\label{tab:positioning}', '')
s = s[:start] + s[end:]
s = s.replace('Table~\\ref{tab:positioning} compares', 'Supplementary Table S11 compares')
p.write_text(s, encoding='utf-8')

p = src / 'supplementary.tex'
s = p.read_text(encoding='utf-8')
assert '\\setcounter{table}{8}' in s and 'tab:positioning' not in s
s = s.replace('\\end{document}', table + '\n\\end{document}')
p.write_text(s, encoding='utf-8')
