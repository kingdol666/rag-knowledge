# -*- coding: utf-8 -*-
"""判卷 documents 修复验收（5 项）+ kb_doc_read 行语义回归。

A. documents 传原生 list（此前被 pydantic 拒）→ 应 ok
B. documents 传 str：合法 JSON + 反斜杠路径 → 应 ok（服务端归一化）
C. documents 传 str：非法转义（单反斜杠）→ 应 status=bad_request + error_kind=bad_request（不再伪装引擎故障）
D. 回归：正斜杠 str → 仍 ok
E. kb_doc_read offset 行语义回归（offset=60/limit=20 → 2000 字符；offset=9200 → 空）
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r'D:/codes/ClaudeGPT/rag_project/rag-knowledge')
MB = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'
BS = chr(92)
DOC = '计算机与人工智能' + BS + 'Lost in the Middle (part 1 of 3).md'
DOC_FS = DOC.replace(BS, '/')
Q = "Why does performance degrade when relevant information is in the middle?"


def mc(tool, args, timeout=240):
    r = subprocess.run(['uv', 'run', '--no-sync', '--directory', str(ROOT / 'backend'), 'python',
                        str(ROOT / 'scripts' / 'mcp_call.py'), tool, json.dumps(args), '--raw'],
                       capture_output=True, text=True, timeout=timeout)
    raw = r.stdout
    i, j = raw.find('{'), raw.rfind('}')
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    results = []

    # A. 原生 list
    r = mc('kb_laya_judge', {"query": Q, "documents": [{"kb_id": MB, "doc_path": DOC_FS}],
                             "criterion": "auto", "include_text": False})
    ok = r.get('status') == 'ok' and bool(r.get('survivors'))
    results.append(('A list 形式', ok, f"status={r.get('status')} survivors={len(r.get('survivors') or [])}"))
    time.sleep(2)

    # B. str + 反斜杠路径（服务端归一化）
    r = mc('kb_laya_judge', {"query": Q, "documents": json.dumps([{"kb_id": MB, "doc_path": DOC}]),
                             "criterion": "auto", "include_text": False})
    ok = r.get('status') == 'ok' and bool(r.get('survivors'))
    results.append(('B str+反斜杠（归一化）', ok, f"status={r.get('status')} survivors={len(r.get('survivors') or [])}"))
    time.sleep(2)

    # C. str + 非法转义 → bad_request 分类
    inner_bad = '[{"kb_id":"%s","doc_path":"%s"}]' % (MB, DOC)
    r = mc('kb_laya_judge', {"query": Q, "documents": inner_bad, "criterion": "auto"})
    err0 = (r.get('errors') or [{}])[0]
    ok = r.get('status') == 'bad_request' and err0.get('error_kind') == 'bad_request'
    results.append(('C 非法转义→bad_request 分类', ok,
                    f"status={r.get('status')} error_kind={err0.get('error_kind')}"))

    # D. 回归：正斜杠 str
    r = mc('kb_laya_judge', {"query": Q, "documents": json.dumps([{"kb_id": MB, "doc_path": DOC_FS}]),
                             "criterion": "auto", "include_text": False})
    ok = r.get('status') == 'ok' and bool(r.get('survivors'))
    results.append(('D 正斜杠 str 回归', ok, f"status={r.get('status')} survivors={len(r.get('survivors') or [])}"))
    time.sleep(2)

    # E. kb_doc_read 行语义回归
    a = mc('kb_doc_read', {"kb_id": MB, "doc_path": DOC_FS, "max_chars": 2000, "offset": 60, "limit": 20})
    b = mc('kb_doc_read', {"kb_id": MB, "doc_path": DOC_FS, "max_chars": 2000, "offset": 9200})
    ok_a = len(a.get('content') or '') > 0
    ok_b = len(b.get('content') or '') == 0 and (b.get('totalLines') or 0) > 0
    results.append(('E1 offset=60 行 → 有内容', ok_a, f"chars={len(a.get('content') or '')}"))
    results.append(('E2 offset=9200 越界 → 空', ok_b, f"chars={len(b.get('content') or '')} totalLines={b.get('totalLines')}"))

    print('=' * 60)
    all_ok = True
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:28s} {detail}")
        all_ok &= ok
    print('=' * 60)
    print('ACCEPTANCE:', 'PASS' if all_ok else 'FAIL')
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
