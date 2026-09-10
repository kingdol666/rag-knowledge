"""多 Harness e2e — 真实子进程 + 真实 LLM 双场景（对齐 multi-harness-architecture.md §5.7）。

用法:
    python scripts/e2e_multi_harness.py [harness_id]     # 默认 mock
    python scripts/e2e_multi_harness.py all --quick      # 探测全部已装引擎并逐一跑场景A

场景 A（工具闭环替代形）: 真实引擎单次补全 → 结构化解析 → 落回标准化结果。
场景 B（meditation 形态): 模拟冥想 prompt → meditation_result JSON 提取。

约定: 引擎未安装 / 无凭据 → 退出码 2（有因 SKIP ≠ 失败）；真实失败 → 退出码 1。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services import harness_registry as hreg          # noqa: E402
from app.services.agent_harness_manager import agent_harness  # noqa: E402

SKIP_EXIT = 2


def _print(name: str, ok: bool, detail: str = "") -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}" + (f" — {detail[:160]}" if detail else ""))


async def scenario_a(harness: str, timeout: int = 120) -> bool:
    """单次补全：真实 LLM 结构化输出（低 token：一句话问答）。"""
    res = await agent_harness.complete(
        prompt="用一句中文回答：1+1 等于几？只回答算式结果，不要解释。",
        kb_config={"harness": harness, "timeout_sec": timeout},
        timeout_sec=timeout,
    )
    _print("A: one-shot completion", res["success"],
           res.get("text") or res.get("error") or "")
    return bool(res["success"])


async def scenario_b(harness: str) -> bool:
    """meditation 形态：meditation_result JSON 提取 → 标准化结果。"""
    from app.services import harness_runner as hrun

    task_prompt = (
        "你是知识库经验合成助手。\n"
        "目标知识库: e2e-demo (id=kb-e2e, path=demo)\n"
        "待处理信号: 1 条\n"
        "## 输出格式要求\n"
        "你的最后一条消息必须且仅包含以下 JSON：\n"
        '```json\n{"meditation_result": {"kb_id": "kb-e2e", "experiences_created": [], '
        '"drafts_created": [], "skipped": [], "total_signals_processed": 0, "summary": "..."}}\n```\n'
        "现在处理信号：问题「如何验证 harness 集成？」—— 若信号不足以产出经验请返回空列表。"
    )
    engine = await hrun.run_engine(
        harness, task_prompt,
        {"harness": harness, "timeout_sec": 600, "no_tools": True},
        run_label=f"e2e-{harness}-b")
    if not engine["success"]:
        _print("B: meditation run", False, engine.get("error") or "")
        return False
    result = hrun.meditation_result_from_text(engine.get("text", ""))
    _print("B: meditation_result 提取", result["success"],
           f"kb_id={result.get('kb_id')} signals={result.get('total_signals_processed')}")
    return bool(result["success"])


async def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    target = args[0] if args else "mock"
    timeout = 90 if quick else 600

    if target == "all":
        targets = []
        for hid in hreg.HARNESS_IDS:
            try:
                probe = await hreg.probe_harness(hid)
            except Exception:
                probe = {"installed": False}
            if probe.get("installed"):
                targets.append(hid)
            else:
                print(f"SKIP {hid}: not installed")
        if not targets:
            print("No harnesses installed — nothing to run")
            return SKIP_EXIT
    else:
        if target == "heuristic":
            print("SKIP heuristic: in-process fallback, nothing to e2e")
            return SKIP_EXIT
        try:
            probe = await hreg.assert_harness_usable(target)
        except hreg.UnknownHarnessError:
            print(f"FAIL: unknown harness '{target}'. Supported: {', '.join(hreg.HARNESS_IDS)}")
            return 1
        except hreg.HarnessUnavailableError as e:
            print(f"SKIP {target}: {e}")
            return SKIP_EXIT
        targets = [target]

    failures = 0
    for hid in targets:
        print(f"\n=== e2e [{hid}]{' (quick)' if quick else ''} ===")
        try:
            ok_a = await scenario_a(hid, timeout=timeout)
            ok_b = True
            if not quick:
                ok_b = await scenario_b(hid)
        except Exception as e:
            _print(f"{hid} unexpected", False, str(e))
            failures += 1
            continue
        if not (ok_a and ok_b):
            failures += 1

    print(f"\nDone: {len(targets)} harness(es), {failures} failure(s)"
          + (" [quick: A only]" if quick else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
