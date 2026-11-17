# -*- coding: utf-8 -*-
"""A5+A6：Lost in the Middle 三卷入库 + 标签 + 索引 + 图谱（走 MCP 工具面）。"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r'D:/codes/ClaudeGPT/rag_project/rag-knowledge').resolve()
ART = (ROOT / 'review' / 'api-demo-20261101' / 'artifacts').resolve()
KB = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'
OUT = (ROOT / 'backend' / 'output' / '40bcd8c6eba7').resolve()

DESCS = {
 1: "【Part 1/3 · Title–§4.2】Lost in the Middle（Liu et al., arXiv 2307.03172）：多文档问答与键值检索两个任务的设置（20 篇维基文档、答案位置循环），GPT-3.5/GPT-4/Claude/MPT-30B/Llama-2 呈现性能首尾高、中段显著下降的 U 形曲线，并分析架构与查询感知上下文化的影响。可答：动机、实验设计、U 形结论。不含：附录。",
 2: "【Part 2/3 · §4.3–附录E】同论文（arXiv 2307.03172）：指令微调对位置稳健性的影响、开放域 QA「更多上下文是否更好」的对比、相关工作与结论，并含参考文献及附录 A–E（消歧干扰项、随机干扰项、干扰项顺序随机化、GPT-4/Llama-2 性能）。可答：指令微调结论、上下文长度利弊、相关工作脉络、附录 A–E 实验。不含：token 计数与完整结果表。",
 3: "【Part 3/3 · 附录F–G.3】同论文（arXiv 2307.03172）：token 计数统计（附录 F）与 10/20/30 篇检索文档下的完整多文档问答结果表（附录 G、G.1–G.3）。可答：各设置的 token 用量与完整结果数值。不含：正文论证与参考文献。",
}
TAGS = ["long-context", "language-model-evaluation", "multi-document-qa",
        "key-value-retrieval", "serial-position-effect"]


def safe_write(target: Path, payload: dict) -> Path:
    """禁止越出 ART 目录的写入。"""
    target = target.resolve()
    if ART not in target.parents:
        raise ValueError(f"refusing to write outside artifacts dir: {target}")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


def mc(tool, args, timeout=300):
    r = subprocess.run(['uv', 'run', '--no-sync', '--directory', str(ROOT / 'backend'), 'python',
                        str(ROOT / 'scripts' / 'mcp_call.py'), tool, json.dumps(args), '--raw'],
                       capture_output=True, text=True, timeout=timeout)
    raw = r.stdout
    i, j = raw.find('{'), raw.rfind('}')
    try:
        return json.loads(raw[i:j + 1]) if i >= 0 else {}
    except Exception:
        return {"_raw": raw[:200]}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    imgs = sorted((OUT / 'images').glob('*.jpg'))
    up = 0
    for p in imgs:
        r = mc('fs_upload_file', {'file_path': str(p), 'parent_id': KB,
                                  'description': f'Lost in the Middle 论文解析图：{p.name}'}, timeout=120)
        up += 1 if r.get('success') else 0
    print(f"images uploaded: {up}/{len(imgs)}", flush=True)

    docs = []
    for i in (1, 2, 3):
        f = next(OUT.glob(f'*part {i} of 3*.md'))
        content = f.read_text(encoding='utf-8')
        name = f'Lost in the Middle (part {i} of 3).md'
        r = mc('kb_doc_create', {'kb_id': KB, 'name': name, 'content': content,
                                 'description': DESCS[i]})
        ok = bool(r.get('success') or r.get('files'))
        path = (r.get('files') or [{}])[0].get('path') or f'计算机与人工智能\\{name}'
        print(f"create part{i}: ok={ok} path={path}", flush=True)
        docs.append((i, path))
        time.sleep(1)
    for i, path in docs:
        r = mc('kb_doc_update_tags', {'kb_id': KB, 'doc_path': path, 'tags': TAGS})
        print(f"tags part{i}: {r.get('success')}", flush=True)
    for i, path in docs:
        r = mc('kb_index_document', {'kb_id': KB, 'doc_path': path})
        vi = (r.get('vector_index') or {})
        print(f"index part{i}: chunks={vi.get('total_chunks')} collection={str(vi.get('collection'))[:40]}", flush=True)
    r = mc('kb_graph_build', {'kb_id': KB, 'force': True})
    tid = r.get('task_id')
    print('graph build task:', tid, flush=True)
    if tid:
        for _ in range(60):
            time.sleep(5)
            ts = mc('kb_task_status', {'task_id': tid})
            if str(ts.get('status', '')).lower() in ('done', 'completed', 'success', 'finished'):
                print('graph build done', flush=True)
                break
    print('report:', safe_write(ART / 'lostmiddle_ingest.json',
                                {'docs': [{'part': i, 'path': p} for i, p in docs]}))


if __name__ == '__main__':
    main()
