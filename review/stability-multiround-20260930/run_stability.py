#!/usr/bin/env python3
"""run_stability — 三模式 × 三任务 × 多轮稳定性矩阵（chat API，默认非流式）。

模式定义（对应当前 chat API 双车道 + 混合语义）：
  A 向量快车道   : kbEnhanced + 指定库（API 注入向量车道提示）
  B 逐级检索通道 : kbEnhanced + 不指定库（API 注入逐级主干提示，无向量工具）
  C 混合         : kbEnhanced + 指定库 + prompt 追加"先向量判定、不足再逐级补全"

任务（均带可核验 ground truth）：
  attention  : Transformer 自注意力公式      → 计算机与人工智能(131篇) Attention Is All You Need
  seismology : 地震波分类与区别（P/S/面波）  → 自然科学与地球科学(75篇) seismology 论文
  pickles    : 四川泡菜腌制（语料库中不存在）→ 期望如实奉告（反幻觉契约）

用法：python run_stability.py r1 r2        # 轮次可任选
输出：results/r{round}_{task}_{mode}.json + 控制台进度行（flush 实时）
"""
import http.client
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'
KB_CS = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'   # 计算机与人工智能
KB_NS = '1e6199ea-f380-44e2-94fc-d431f0f9bb6b'   # 自然科学与地球科学

TASKS = {
    'attention': {
        'prompt': 'Transformer 的自注意力机制（self-attention）的计算公式是什么？',
        'pin': KB_CS,
    },
    'seismology': {
        'prompt': '地震波主要分为哪几类？它们有什么区别？',
        'pin': KB_NS,
    },
    'pickles': {
        'prompt': '如何腌制四川泡菜？',
        'pin': KB_CS,   # 故意指定一个不含此内容的库 → 期望如实奉告
    },
}
HYBRID_SUFFIX = ('【混合检索模式】先用 kb_search_two_stage / kb_search_vector 宽网检索'
                 '并用 kb_laya_judge 判定；若幸存证据不足以回答，再用 kb_list → '
                 'kb_get_documents 逐级检索补齐后才作答。')


def token() -> str:
    for line in (REPO / '.env').read_text(encoding='utf-8').splitlines():
        if line.startswith('MCP_AUTH_TOKEN='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('MCP_AUTH_TOKEN not in .env')


def run_once(round_no: int, task: str, mode: str) -> dict:
    spec = TASKS[task]
    prompt = spec['prompt']
    kb_ids = [spec['pin']] if mode in ('A', 'C') else []
    if mode == 'C':
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
    try:
        conn.request('POST', '/api/claude/chat', body=json.dumps(body),
                     headers={'Content-Type': 'application/json',
                              'Authorization': f'Bearer {token()}'})
        resp = conn.getresponse()
        raw = resp.read().decode('utf-8')
    finally:
        conn.close()
    wall = time.time() - t0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {'success': False, 'error': raw[:300]}
    rec = {
        'round': round_no, 'task': task, 'mode': mode,
        'http': resp.status, 'wall_s': round(wall, 1),
        'success': payload.get('success'),
        'session_id': payload.get('sessionId'),
        'turns': payload.get('num_turns'),
        'cost': payload.get('total_cost_usd'),
        'duration_ms': payload.get('duration_ms'),
        'answer': payload.get('answer') or payload.get('error', ''),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / f'r{round_no}_{task}_{mode}.json').write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    return rec


if __name__ == '__main__':
    rounds = sys.argv[1:] or ['r1']
    total = len(rounds) * len(TASKS) * 3
    done = 0
    for rnd in rounds:
        n = int(rnd[1:]) if rnd.startswith('r') else int(rnd)
        for task in TASKS:
            for mode in ('A', 'B', 'C'):
                done += 1
                tag = f'{rnd}_{task}_{mode}'
                print(f'[{done}/{total}] RUN {tag} …', flush=True)
                try:
                    rec = run_once(n, task, mode)
                    head = (rec['answer'] or '').replace('\n', ' ')[:120]
                    print(f'  → HTTP {rec["http"]} · {rec["wall_s"]}s · ok={rec["success"]} '
                          f'· turns={rec["turns"]} · ${rec["cost"]} · sess={str(rec["session_id"])[:12]}\n'
                          f'    {head}', flush=True)
                except Exception as exc:  # noqa: BLE001 — 记录后继续下一跑
                    print(f'  → EXCEPTION {type(exc).__name__}: {exc}', flush=True)
                    (OUT / f'{tag}_EXCEPTION.txt').write_text(
                        f'{type(exc).__name__}: {exc}', encoding='utf-8')
    print('STABILITY-RUNS-DONE', flush=True)
