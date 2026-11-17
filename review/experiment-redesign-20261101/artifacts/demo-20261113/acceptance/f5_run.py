# -*- coding: utf-8 -*-
"""F5 acceptance: launch agent/chat omp harness tasks (async) and poll to terminal state."""
import json, time, sys, io, urllib.request

BASE = "http://127.0.0.1:6789"
TOKEN = "sk-HLF27pnFAnkOunmRZSooP9rD9MogAguF4yZ2aBRM1Gs"
ACC = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\experiment-redesign-20261101\artifacts\demo-20261113\acceptance"

REQ_TMPL = """基于知识库回答：{q}
要求：按 QDCVR 流程（改写→kb_search_vector 宽网→kb_laya_judge 引用式判卷→kb_doc_read 逐字核验），答案给出引用文档 doc_path 并逐字引用关键句，标注可信度。检索不到的如实报告未找到，禁止编造。"""

Q1 = REQ_TMPL.format(q="TinyBERT 用什么方法训练、相比 BERTBASE 在 GLUE 上表现如何（准确率与体积/速度倍数）？另外问答系统按领域分为哪两大类？")
Q2 = REQ_TMPL.format(q="2026 年诺贝尔文学奖得主是谁？其获奖作品的知识库文档路径是什么？")

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Content-Type", "application/json")
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8", "replace")[:2000]}

def launch(q):
    body = {"prompt": q, "harness": "omp", "permission": "bypassPermissions", "mode": "async", "timeout_ms": 1100000}
    r = api("POST", "/api/kb/agent/chat", body)
    print("LAUNCH:", json.dumps(r, ensure_ascii=False)[:800])
    return r

def poll(task_id, max_s=1200):
    t0 = time.time()
    last = None
    while time.time() - t0 < max_s:
        time.sleep(10)
        last = api("GET", f"/api/kb/agent/tasks/{task_id}")
        status = last.get("status", "?")
        print(f"[{int(time.time()-t0)}s] status={status}", flush=True)
        if status in ("done", "completed", "failed", "error", "timeout", "cancelled"):
            return last, round(time.time() - t0, 1)
    return last, round(time.time() - t0, 1)

if __name__ == "__main__":
    which = sys.argv[1]
    q, outfile = (Q1, "f5_q1.json") if which == "q1" else (Q2, "f5_q2.json")
    t0 = time.time()
    r = launch(q)
    tid = r.get("task_id") or r.get("taskId")
    final, secs = poll(tid) if tid else (r, 0)
    rec = {"q": which, "task_id": tid, "status": final.get("status"), "seconds": secs,
           "launch": r, "final": final, "prompt": q}
    with io.open(ACC + "\\" + outfile, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print("SAVED", outfile, "status=", rec["status"], "seconds=", secs)
