import io, re
s = io.open('main.tex', encoding='utf-8').read()
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', s, re.S)
body = re.sub(r'\\[a-zA-Z]+', ' ', m.group(1))
body = body.replace('{', ' ').replace('}', ' ')
print('abstract words ~', len(body.split()))
