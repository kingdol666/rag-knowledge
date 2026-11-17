# -*- coding: utf-8 -*-
"""spec 对账修复：跨轮有损条目重建 + 重复文件清理。

1) science-en：清掉与 .pdf 同名的陈旧 .md（PDF 字节误存副本）；孤立 .md(PDF 字节) 改名 .pdf；
   确保已知 12+3 篇论文条目齐全（锚/问题来自 expand_corpus 的 papers 表）。
2) tech-en：目录里存在但 spec 缺失的 md 补回条目（昨轮 K8s 文件）。
3) 其他域：存在但 spec 缺失的文件补通用条目（anchor=None）。
运行: python reconcile_spec.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(r'D:/codes/ClaudeGPT/rag_project/rag-knowledge')
BASE = ROOT / 'review/experiment-redesign-20261101'
ART = BASE / 'artifacts'
CORPUS = ROOT / 'corpus/multi-domain-docs-20261101'

sys.path.insert(0, str(BASE / 'scripts'))
# 已知 arXiv 论文表（与 expand_corpus.main 内 papers 一致；那里是局部变量故此处内联）
ARXIV_PAPERS = [
    ("1512.03385", "resnet.md", "Deep Residual Learning", "Deep Residual Learning",
     "Which paper introduced deep residual learning for image recognition?"),
    ("1406.2661", "gan.md", "Generative Adversarial Networks", "Generative Adversarial",
     "Which paper proposed generative adversarial networks?"),
    ("1312.6114", "vae.md", "Auto-Encoding Variational Bayes", "Variational Bayes",
     "Which paper proposed the variational autoencoder?"),
    ("1301.3781", "word2vec.md", "Efficient Estimation of Word Representations", "word representations",
     "Which paper proposed efficient word representations (word2vec)?"),
    ("2103.00020", "clip.md", "Learning Transferable Visual Models", "Natural Language Supervision",
     "Which paper introduced CLIP (visual models from natural language supervision)?"),
    ("2006.11239", "ddpm.md", "Denoising Diffusion Probabilistic Models", "Denoising Diffusion",
     "Which paper introduced denoising diffusion probabilistic models?"),
    ("1910.10683", "t5.md", "Exploring the Limits of Transfer Learning", "Text-to-Text",
     "Which paper proposed the text-to-text transfer learning framework (T5)?"),
    ("1907.11692", "roberta.md", "RoBERTa: A Robustly Optimized BERT", "RoBERTa",
     "Which paper presented RoBERTa?"),
    ("2103.14030", "swin_transformer.md", "Swin Transformer", "Swin Transformer",
     "Which paper introduced the Swin Transformer?"),
    ("2005.14165", "gpt3.md", "Language Models are Few-Shot Learners", "Few-Shot Learners",
     "Which paper showed language models are few-shot learners (GPT-3)?"),
    ("2203.02155", "instructgpt.md", "InstructGPT", "human feedback",
     "Which paper trained language models to follow instructions with human feedback?"),
    ("2302.13971", "llama.md", "LLaMA: Open and Efficient Foundation Language Models", "LLaMA",
     "Which paper introduced LLaMA?"),
]
KNOWN_ARXIV = {name: (title, anchor, question) for ax, name, title, anchor, question in ARXIV_PAPERS}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # ── 1. science-en 重复清理 ──
    removed, renamed = [], []
    for md in (CORPUS / 'science-en').glob('*.md'):
        pdf = md.with_suffix('.pdf')
        if pdf.exists():
            if md.read_bytes()[:5] == b'%PDF-':
                md.unlink()
                removed.append(md.name)
        elif md.read_bytes()[:5] == b'%PDF-':
            md.rename(pdf)
            renamed.append(pdf.name)
    print(f'science-en: removed stale .md ×{len(removed)}, renamed ×{len(renamed)}')

    final_f = ART / 'corpus_spec_final.json'
    spec = json.loads(final_f.read_text(encoding='utf-8'))
    by_slug = {m['slug']: m for m in spec}

    # ── 2. science-en 条目重建 ──
    sci = by_slug.setdefault('science-en', dict(
        slug='science-en', kb_name='MD语料-科学-英文',
        kb_desc='完整论文 PDF（MinerU 解析链入库）', docs=[]))
    have = {d['file'] for d in sci['docs']}
    for name, (title, anchor, question) in KNOWN_ARXIV.items():
        fp = f'science-en/{name}'
        if fp in have or not (CORPUS / fp).exists():
            continue
        sci['docs'].append(dict(file=fp, name=name.replace('.md', ''),
                                desc=f'{title}（arXiv 整篇论文）', anchor=anchor, question=question))
        print(f'restored science-en: {name}')

    # ── 3. 各域：存在但 spec 缺失的文件补通用条目 ──
    domain_of_dir = {'law-zh': 'law-zh', 'gov-zh': 'gov-zh', 'literature-zh': 'literature-zh',
                     'literature-en': 'literature-en', 'science-en': 'science-en',
                     'medicine-en': 'medicine-en', 'tech-en': 'tech-en',
                     'history-zh': 'history-zh', 'philosophy-en': 'philosophy-en',
                     'economics-en': 'economics-en'}
    added = 0
    for dirname, slug in domain_of_dir.items():
        slot = by_slug.get(slug)
        if not slot:
            continue
        have = {d['file'] for d in slot['docs']}
        for p in sorted((CORPUS / dirname).glob('*')):
            if not p.is_file() or p.suffix.lower() not in ('.txt', '.md', '.xml', '.pdf'):
                continue
            rel = f'{dirname}/{p.name}'
            if rel in have:
                continue
            title = p.stem
            try:
                if p.suffix.lower() != '.pdf':
                    head = p.read_text(encoding='utf-8', errors='replace')[:600]
                    for line in head.splitlines():
                        if line.strip() and not line.startswith('<'):
                            title = line.strip()[:60]
                            break
            except Exception:  # noqa: BLE001
                pass
            slot['docs'].append(dict(file=rel, name=p.name,
                                     desc=f'{title}（{dirname} 完整文档）',
                                     anchor=None, question=None))
            added += 1
    print(f'补通用条目 ×{added}')

    final_f.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(len(m['docs']) for m in spec)
    per = {m['slug']: len(m['docs']) for m in spec}
    print('domains=', len(spec), 'docs=', total, json.dumps(per, ensure_ascii=False))


if __name__ == '__main__':
    main()
