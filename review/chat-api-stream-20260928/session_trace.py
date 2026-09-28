#!/usr/bin/env python3
"""session_trace — chat 会话执行过程监控器（chat-db 时间线 + 卡点标记）。

用法：
  python session_trace.py            # 最近一个会话
  python session_trace.py <sid>      # 指定会话
  python session_trace.py <sid> --stall 15   # 卡点阈值（默认 20s）

输出：逐工具调用时间线（含各自耗时）+ 阶段聚合（LLM 间隙 / 工具执行 / 首调用等待）
"""
import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / 'storage' / 'claude-chat.db'
STALL = 20.0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    stall = 20.0
    if '--stall' in sys.argv:
        stall = float(sys.argv[sys.argv.index('--stall') + 1])
    db = sqlite3.connect(str(DB))
    db.row_factory = sqlite3.Row
    if args:
        sid = args[0]
    else:
        row = db.execute("SELECT session_id FROM messages ORDER BY id DESC LIMIT 1").fetchone()
        sid = row['session_id']
    rows = db.execute("SELECT * FROM messages WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    if not rows:
        print(f"no messages for {sid}")
        return 1

    def T(r):
        return datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))

    evs = []
    for r in rows:
        msg = json.loads(r['content'])
        t = T(r)
        mt = r['sdk_type'] or msg.get('type')
        if mt == 'user':
            c = msg.get('message', {}).get('content')
            if isinstance(c, list) and any(b.get('type') == 'tool_result' for b in c):
                evs.append([t, 'resp', '', False])
        elif mt == 'assistant':
            for b in msg.get('message', {}).get('content', []):
                if b.get('type') == 'tool_use':
                    # top-level calls only (parent_tool_use_id non-null = subagent)
                    top = not b.get('parent_tool_use_id')
                    evs.append([t, 'call', b.get('name'), top])
        elif mt == 'result':
            evs.append([t, 'result',
                        f"dur={msg.get('duration_ms')}ms turns={msg.get('num_turns')} cost=${msg.get('total_cost_usd')}",
                        True])
    if not evs:
        print('no tool events')
        return 1
    t0 = evs[0][0]
    prev = None
    llm = tool = 0.0
    stalls = 0
    for t, kind, det, top in evs:
        off = (t - t0).total_seconds()
        gap = (t - prev).total_seconds() if prev else 0.0
        if prev:
            if kind == 'call':
                llm += gap
            elif kind == 'resp':
                tool += gap
        mark = ''
        if gap >= stall and kind in ('call', 'result'):
            mark = f"  ⚠ STALL +{gap:.0f}s"
            stalls += 1
        if kind in ('call', 'result'):
            sub = '' if top else ' [sub]'
            print(f"{off:7.1f}s {gap:6.1f}s CALL{sub} {det[:64]}{mark}")
        prev = t
    first_call = next((e for e in evs if e[1] == 'call'), None)
    warm = (first_call[0] - t0).total_seconds() if first_call else 0
    print(f"\nsession={sid}\nLLM 轮次合计 {llm:.1f}s · 工具执行 {tool:.1f}s · 首个工具调用前 {warm:.1f}s · 卡点(≥{stall:.0f}s) {stalls} 个")
    return 0


if __name__ == '__main__':
    sys.exit(main())
