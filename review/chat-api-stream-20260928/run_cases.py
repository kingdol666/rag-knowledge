#!/usr/bin/env python3
"""run_cases — chat API 找得到/找不到 分组检索案例（2026-09-29）。

案例设计：
  找得到：F1 CoRoT 行星计划(A· pinned 自然科学) / F2 Collins 求婚理由(B· 全库逐级) /
          F3 BERT 预训练任务(C· pinned 计算机与人工智能+混合提示)
  找不到：N1 故宫门票(A· pinned 计算机与人工智能) / N2 周杰伦歌曲(B· 全库逐级) /
          N3 日式寿司(C· pinned 计算机与人工智能+混合提示)
输出：results/case_<id>.json + 控制台一行摘要（耗时/轮次/费用/结果性质）。
"""
import json
import sys
import time
import http.client
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'
KB_CS = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'    # 计算机与人工智能
KB_NAT = '1e6199ea-f380-44e2-94fc-d431f0f9bb6b'   # 自然科学与地球科学
HYBRID = '【混合检索模式】先用 kb_search_two_stage / kb_search_vector 宽网检索并用 kb_laya_judge 判定；若幸存证据不足以回答，再用 kb_list → kb_get_documents 逐级检索补齐后才作答。'

CASES = {
    'F1_corot':   {'kb': [KB_NAT], 'prompt': 'CoRoT 系外行星计划的观测目标是什么？'},
    'F2_collins': {'kb': [],       'prompt': '《傲慢与偏见》中 Mr. Collins 向 Elizabeth 求婚时给出了哪些理由？'},
    'F3_bert':    {'kb': [KB_CS],  'prompt': 'BERT 的预训练任务有哪些？ ' + HYBRID},
    'N1_gugong':  {'kb': [KB_CS],  'prompt': '北京故宫的门票价格是多少？'},
    'N2_jay':     {'kb': [],       'prompt': '周杰伦有哪些代表歌曲？'},
    'N3_sushi':   {'kb': [KB_CS],  'prompt': '如何制作日式寿司？ ' + HYBRID},
}


def token() -> str:
    for line in (REPO / '.env').read_text(encoding='utf-8').splitlines():
        if line.startswith('MCP_AUTH_TOKEN='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('MCP_AUTH_TOKEN not in .env')


def run_once(cid: str) -> dict:
    c = CASES[cid]
    conn = http.client.HTTPConnection('127.0.0.1', 6789, timeout=540)
    body = {'prompt': c['prompt'], 'stream': False, 'kbEnhanced': True, 'kbIds': c['kb'],
            'engine': 'claude', 'permissionMode': 'default', 'timeout_ms': 480000}
    conn.request('POST', '/api/claude/chat', body=json.dumps(body),
                 headers={'Content-Type': 'application/json',
                          'Authorization': f'Bearer {token()}'})
    t0 = time.time()
    resp = conn.getresponse()
    raw = resp.read().decode('utf-8')
    wall = time.time() - t0
    try:
        p = json.loads(raw)
    except json.JSONDecodeError:
        p = {'success': False, 'error': raw[:300]}
    rec = {'case': cid, 'http': resp.status, 'wall_s': round(wall, 1),
           'turns': p.get('num_turns'), 'cost': p.get('total_cost_usd'),
           'answer': p.get('answer') or p.get('error', '')}
    OUT.mkdir(exist_ok=True)
    (OUT / f'case_{cid}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    return rec


if __name__ == '__main__':
    ids = sys.argv[1:] or list(CASES)
    for cid in ids:
        r = run_once(cid)
        head = (r['answer'] or '').replace('\n', ' ')[:130]
        print(f"{cid:12} HTTP {r['http']} · {r['wall_s']}s · {r['turns']}轮 · ${r['cost']}\n    {head}")
        sys.stdout.flush()
