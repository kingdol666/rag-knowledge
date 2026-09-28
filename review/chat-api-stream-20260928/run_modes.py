#!/usr/bin/env python3
"""run_modes — chat API 三模式 × 双题检索矩阵（2026-09-29）。

模式定义（对应当前 chat API 双车道 + 混合语义）：
  A 向量快车道   : kbEnhanced + 指定库（API 注入向量车道提示）
  B 逐级检索通道 : kbEnhanced + 不指定库（API 注入逐级主干提示，无向量工具）
  C 混合         : kbEnhanced + 指定库 + 用户 prompt 内追加"先向量判定、不足再逐级补全"

输出：results/<题>_<模式>.json（完整回答）+ 控制台紧凑表。
"""
import json
import sys
import time
import http.client
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'
KB_CS = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'   # 计算机与人工智能（131 篇，含 Transformer 原论文）

QUESTIONS = {
    'transformer': 'Transformer 的自注意力机制（self-attention）的计算公式是什么？',
    'hongshaorou': '红烧肉怎么做？',
}
HYBRID_SUFFIX = '【混合检索模式】先用 kb_search_two_stage / kb_search_vector 宽网检索并用 kb_laya_judge 判定；若幸存证据不足以回答，再用 kb_list → kb_get_documents 逐级检索补齐后才作答。'


def token() -> str:
    for line in (REPO / '.env').read_text(encoding='utf-8').splitlines():
        if line.startswith('MCP_AUTH_TOKEN='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('MCP_AUTH_TOKEN not in .env')


def run_once(qkey: str, mode: str) -> dict:
    prompt = QUESTIONS[qkey]
    if mode == 'A':
        kb_ids = [KB_CS]
    elif mode == 'B':
        kb_ids = []
    else:  # C
        kb_ids = [KB_CS]
        prompt = prompt + ' ' + HYBRID_SUFFIX
    body = {
        'prompt': prompt,
        'kbEnhanced': True,
        'kbIds': kb_ids,
        'engine': 'claude',
        'permissionMode': 'default',
        'timeout_ms': 480000,
    }
    conn = http.client.HTTPConnection('127.0.0.1', 6789, timeout=540)
    t0 = time.time()
    conn.request('POST', '/api/claude/chat', body=json.dumps(body),
                 headers={'Content-Type': 'application/json',
                          'Authorization': f'Bearer {token()}'})
    resp = conn.getresponse()
    raw = resp.read().decode('utf-8')
    wall = time.time() - t0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {'success': False, 'error': raw[:300]}
    rec = {'q': qkey, 'mode': mode, 'http': resp.status, 'wall_s': round(wall, 1),
           'turns': payload.get('num_turns'), 'cost': payload.get('total_cost_usd'),
           'answer': payload.get('answer') or payload.get('error', '')}
    OUT.mkdir(exist_ok=True)
    (OUT / f'{qkey}_{mode}.json').write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    return rec


if __name__ == '__main__':
    todo = sys.argv[1:] or ['transformer_A', 'transformer_B', 'transformer_C',
                            'hongshaorou_A', 'hongshaorou_B', 'hongshaorou_C']
    for item in todo:
        qkey, mode = item.rsplit('_', 1)
        rec = run_once(qkey, mode)
        head = (rec['answer'] or '').replace('\n', ' ')[:150]
        print(f"{item:18} HTTP {rec['http']} · {rec['wall_s']}s · turns={rec['turns']} · ${rec['cost']}\n    {head}")
        sys.stdout.flush()
