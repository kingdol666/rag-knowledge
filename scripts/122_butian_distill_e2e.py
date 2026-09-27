#!/usr/bin/env python3
"""butian 链路闭环实测: musk 种子 → ragctl soul distill 落地 → qdcvr 问答 → 清理.

对应 butian SKILL.md Step 3(转换,已由 nuwa_to_seed 验证) → Step 4(落地) → Step 6(使用).
种子包: review/skill-fulltest-20260927/distill/musk-seed (来自真实 musk-perspective).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

SOUL = "soul-skillaudit-musk"
SEED = REPO / "review/skill-fulltest-20260927/distill/musk-seed"
NODE = REPO / "command" / "ragctl.js"


def run(args, timeout=300):
    """参数列表执行, 不经 shell(防注入)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           cwd=str(REPO), shell=False)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def main() -> int:
    ok_all = True
    mc = McpClient()
    try:
        # 0) 预检: 种子包契约
        need = ["meta.json", "persona.md", "work.md", "values.md"]
        missing = [f for f in need if not (SEED / f).exists()]
        print(("PASS" if not missing else "FAIL"), "seed 契约:", "齐全" if not missing else f"缺 {missing}")
        ok_all &= not missing

        # 1) ragctl soul distill 落地 (butian Step 4)
        rc, out = run(["node", str(NODE), "soul", "distill", str(SEED),
                       "--name", SOUL, "--labels", "skill-audit",
                       "--values", str(SEED / "values.md")])
        landed = rc == 0 and (SOUL in out or "docs_created" in out or "success" in out.lower())
        print(("PASS" if landed else "FAIL"), f"ragctl soul distill rc={rc}:", out[-300:].replace("\n", " | "))
        ok_all &= landed

        # 2) soul_list 可见 + 4 宪法文档
        lst = json.dumps(mc.call("soul_list", {}, timeout=60), ensure_ascii=False)
        visible = SOUL in lst
        print(("PASS" if visible else "FAIL"), "soul_list 可见:", visible)
        ok_all &= visible
        docs = mc.call("kb_get_documents", {"kb_id": SOUL, "lightweight": True}, timeout=60)
        names = [d.get("name", "") for d in (docs.get("catalog") or [])]
        has4 = any("definition" in n for n in names) and any("thinking" in n for n in names) \
            and any("values" in n for n in names)
        print(("PASS" if has4 else "FAIL"), f"宪法文档({len(names)}):", names)
        ok_all &= has4

        # 3) 等索引任务结束 (落地时异步)
        time.sleep(6)

        # 4) soul_qdcvr_ask 人格作答 (butian Step 6; 显式 soul_kb_id, 不依赖路由)
        r = mc.call("soul_qdcvr_ask",
                    {"query": "用你自己的思维方式回答: 面对一个成本高昂的复杂系统, 你的第一步是什么?",
                     "soul_kb_id": SOUL, "top_k": 3, "async_mode": True}, timeout=120)
        tid = r.get("task_id", "")
        ans_ok, answer = False, ""
        if tid:
            deadline = time.time() + 240
            while time.time() < deadline:
                fin = mc.call("kb_task_status", {"task_id": tid}, timeout=60)
                if str(fin.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                    res = fin.get("result") or {}
                    answer = str(res.get("answer", ""))
                    ans_ok = len(answer) > 40
                    break
                time.sleep(5)
        print(("PASS" if ans_ok else "FAIL"), f"qdcvr 人格作答({len(answer)}字):", answer[:100].replace("\n", " "))
        ok_all &= ans_ok

        # 5) 清理
        mc.call("soul_delete", {"soul_kb_id": SOUL}, timeout=120)
        gone = SOUL not in json.dumps(mc.call("soul_list", {}, timeout=60), ensure_ascii=False)
        print(("PASS" if gone else "FAIL"), "清理无残留:", gone)
        ok_all &= gone
    finally:
        try:
            mc.call("soul_delete", {"soul_kb_id": SOUL}, timeout=60)
        except Exception:
            pass
        mc.close()
    print("RESULT:", "ALL PASS" if ok_all else "HAS FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
