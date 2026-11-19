from pathlib import Path
import hashlib
import re
import shutil
import sys


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(root: Path, path: str) -> set[str]:
    text = re.sub(r'(?<!\\)%[^\n]*', '', (root/path).read_text(encoding='utf-8'))
    nested = [p if p.endswith('.tex') else p+'.tex' for p in re.findall(r'\\input\{([^}]+)\}', text)]
    figures = [Path('figs', p if p.endswith('.pdf') else p+'.pdf').as_posix()
               for p in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text)]
    return {path, *figures}.union(*(dependencies(root, p) for p in nested))


def capture(root: Path, snap: Path) -> None:
    main = dependencies(root, 'main_20p.tex')
    supp = dependencies(root, 'supplementary.tex')
    assert (len([p for p in main if p.startswith('figs/')]), len([p for p in supp if p.startswith('figs/')])) == (9, 5)
    assert 'figs/fig_opt_verifier.pdf' in main and 'figs/fig_opt_s_margin.pdf' in supp
    files = main | supp | {'main_20p.aux', 'main_20p.bbl', 'main_20p.pdf', 'main_20p.log',
                          'supplementary.aux', 'supplementary.pdf', 'supplementary.log', 'highlights.tex'}
    for stem, group in [('main_20p', main), ('supplementary', supp)]:
        latest = max((root/p).stat().st_mtime_ns for p in group)
        assert all((root/(stem+ext)).stat().st_mtime_ns >= latest for ext in ('.pdf','.aux')), (stem, 'stale compilation')
    assert (root/'main_20p.aux').stat().st_mtime_ns >= (root/'main_20p.bbl').stat().st_mtime_ns
    before = {key: file_hash(root/key) for key in sorted(files)}
    for key, sha in before.items():
        with (snap/key).open('xb') as out:
            out.write((root/key).read_bytes())
        shutil.copystat(root/key, snap/key)
        assert file_hash(snap/key) == sha, f'{key} changed while copying'
    assert all(file_hash(root/key) == sha for key, sha in before.items()), 'Frozen inputs changed during snapshot'
    with (snap/'SHA256SUMS.txt').open('x', encoding='utf8') as out:
        out.writelines(f'{sha}  {name}\n' for name, sha in before.items())
    print(f'Snapshotted {len(files)} frozen files; Figure 9 {before["figs/fig_opt_verifier.pdf"]}; Figure S4 {before["figs/fig_opt_s_margin.pdf"]}')
    body = (snap/'highlights.tex').read_text(encoding='utf8').strip()
    assert re.fullmatch(r'\\begin\{highlights\}\s*(?:\\item[ \t]+[^\n]+\n){5}\\end\{highlights\}', body)
    with (snap.parent/'highlights_flattened.tex').open('x', encoding='utf8') as out:
        out.write('\\begin{document}\n' + body.replace('{highlights}', '{itemize}') + '\n\\end{document}\n')


def verify(root: Path, snap: Path) -> None:
    for line in (snap/'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        sha, name = line.split('  ', 1)
        assert file_hash(snap/name) == sha and file_hash(root/name) == sha, f'Frozen input drift: {name}'
    print('Original and snapshot hashes still match for every frozen input.')


if __name__ == '__main__':
    {'capture': capture, 'verify': verify}[sys.argv[1]](*map(Path, sys.argv[2:]))
