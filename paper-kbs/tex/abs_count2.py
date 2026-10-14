import io, re
s = io.open('main.tex', encoding='utf-8').read()
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', s, re.S)
body = m.group(1)
body = re.sub(r'\$[^$]*\$', 'MATH', body)
body = re.sub(r'\\[a-zA-Z]+', ' ', body)
body = body.replace('{', ' ').replace('}', ' ')
print('abstract real words ~', len(body.split()))
# hnsw mention lines
for i, line in enumerate(s.splitlines(), 1):
    if 'HNSW' in line:
        print(i, line.strip()[:90])
