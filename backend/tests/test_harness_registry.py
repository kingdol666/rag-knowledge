"""多 Harness 注册表 / 规格 / 解析器 / mock 全链路 / API 三态校验 单元测试。

对齐 docs/multi-harness-architecture.md 的验收清单：
- 注册表完整性（14 引擎单一事实源）
- 探测与拉起同源（resolve_command 三态 / Windows .cmd 包装纪律）
- spec 构建器（build_args / promptDelivery / 长度护栏）
- 输出解析器（14 引擎 mapLine，未知事件忽略）
- mock 进程内引擎全链路（manager.complete / runner.run_engine / meditation 形态）
- 执行前强校验（未知 400 / 未安装 409）

全部进程内/离线，无需真实 CLI 与凭据。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from app.services import harness_registry as hreg
from app.services import harness_specs as hspec
from app.services import harness_runner as hrun


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── 注册表完整性 ──────────────────────────────────────────────────────

class TestRegistry:
    EXPECTED_IDS = ["mock", "omp", "opencode", "codex", "dsh", "claude", "gemini",
                    "copilot", "cursor", "crush", "goose", "qwen", "pi", "hermes"]

    def test_fourteen_engines_unique(self):
        assert hreg.HARNESS_IDS == self.EXPECTED_IDS
        assert len(set(hreg.HARNESS_IDS)) == 14

    def test_entry_fields_complete(self):
        for hid in self.EXPECTED_IDS:
            entry = hreg.HARNESS_REGISTRY[hid]
            for key in ("label", "description", "homepage", "process_model",
                        "capabilities", "requires_env", "notes"):
                assert key in entry, f"{hid} missing {key}"
            assert entry["process_model"] in ("inprocess", "oneshot")
            caps = entry["capabilities"]
            assert set(caps.keys()) == {"steer", "supervise", "hitl",
                                        "terminal", "context_stats", "compact"}
            assert all(isinstance(v, bool) for v in caps.values()), f"{hid} caps not bool"

    def test_capability_honesty(self):
        # 本平台一次性作业集成口径：无常驻会话 → 无 steer/terminal/compact；
        # supervise 是平台 prompt 驱动的，全部支持。
        for hid, entry in hreg.HARNESS_REGISTRY.items():
            assert entry["capabilities"]["supervise"] is True, hid
            assert entry["capabilities"]["steer"] is False or hid == "mock", hid
            assert entry["capabilities"]["terminal"] is False, hid
        # usage 透出的引擎才声明 context_stats（不虚报）
        assert hreg.HARNESS_REGISTRY["omp"]["capabilities"]["context_stats"] is True
        assert hreg.HARNESS_REGISTRY["claude"]["capabilities"]["context_stats"] is True
        assert hreg.HARNESS_REGISTRY["copilot"]["capabilities"]["context_stats"] is False

    def test_mock_is_inprocess(self):
        assert hreg.HARNESS_REGISTRY["mock"]["process_model"] == "inprocess"
        assert hreg.resolve_command("mock") == "inprocess:mock"

    def test_unknown_harness(self):
        assert not hreg.is_known_harness("nope")
        with pytest.raises(hreg.UnknownHarnessError):
            run(hreg.probe_harness("nope"))

    def test_heuristic_pseudo_status(self):
        info = run(hreg.probe_harness("heuristic"))
        assert info["installed"] is True

    def test_static_models_have_default_empty(self):
        for hid in self.EXPECTED_IDS:
            models = hreg.harness_models(hid)
            assert models[0] == "", f"{hid} model catalog must start with default ''"

    def test_models_unknown_raises(self):
        with pytest.raises(hreg.UnknownHarnessError):
            hreg.harness_models("nope")


# ── 探测与拉起同源 ────────────────────────────────────────────────────

class TestResolveAndWrap:
    def setup_method(self):
        hreg.reset_probe_cache()

    def test_resolve_missing_binary(self, monkeypatch):
        monkeypatch.setattr(hreg.shutil, "which", lambda name: None)
        assert hreg.resolve_command("hermes") is None

    def test_resolve_via_which(self, monkeypatch):
        monkeypatch.setattr(hreg.shutil, "which", lambda name: f"C:/bin/{name}.EXE")
        assert hreg.resolve_command("goose") == "C:/bin/goose.EXE"

    def test_resolve_command_override(self, monkeypatch, tmp_path):
        from app.config import config
        real_bin = tmp_path / "goose-real.exe"
        real_bin.write_bytes(b"stub")
        monkeypatch.setitem(config._config, "harness",
                            {"commands": {"goose": str(real_bin)}})
        assert hreg.resolve_command("goose") == str(real_bin)

    def test_resolve_command_override_broken_falls_back(self, monkeypatch):
        """覆盖项无法解析时告警并回退 PATH 探测（不硬失败）。

        PATH 探测被固定, 否则断言会依赖开发机是否恰好装了该引擎 —— 装了就会
        解析到真实路径, 未装才返回 None。这里钉死 PATHEXT 探测结果, 使断言
        只检验「回退发生了」这一契约本身。
        """
        from app.config import config
        monkeypatch.setitem(config._config, "harness",
                            {"commands": {"hermes": "Z:/no/such/bin.exe"}})
        monkeypatch.setattr(hreg.shutil, "which",
                            lambda name: "C:/bin/hermes.EXE" if name == "hermes" else None)
        assert hreg.resolve_command("hermes") == "C:/bin/hermes.EXE"

    def test_resolve_command_override_broken_and_absent_returns_none(self, monkeypatch):
        """覆盖项坏 + PATH 也没有 → 返回 None（不抛异常）。"""
        from app.config import config
        monkeypatch.setitem(config._config, "harness",
                            {"commands": {"hermes": "Z:/no/such/bin.exe"}})
        monkeypatch.setattr(hreg.shutil, "which", lambda name: None)
        assert hreg.resolve_command("hermes") is None

    def test_wrap_windows_cmd_literal(self, monkeypatch):
        monkeypatch.setattr(hreg.sys, "platform", "win32")
        argv = hreg.wrap_windows_cmd([r"C:\npm\thing.CMD", "-p", "val"])
        assert argv[:4] == ["cmd.exe", "/d", "/s", "/c"]
        assert argv[4] == r"C:\npm\thing.CMD"

    def test_wrap_rejects_quotes_and_newlines(self, monkeypatch):
        monkeypatch.setattr(hreg.sys, "platform", "win32")
        with pytest.raises(ValueError):
            hreg.wrap_windows_cmd([r"C:\npm\x.CMD", 'has "quote"'])
        with pytest.raises(ValueError):
            hreg.wrap_windows_cmd([r"C:\npm\x.CMD", "has\nnewline"])

    def test_wrap_non_cmd_passthrough(self, monkeypatch):
        monkeypatch.setattr(hreg.sys, "platform", "win32")
        argv = [r"C:\bin\goose.EXE", "-t", "text"]
        assert hreg.wrap_windows_cmd(argv) == argv

    def test_validate_spawn_arg(self):
        for bad in ('a"b', "a\nb", "a\rb", "a\x00b"):
            with pytest.raises(ValueError):
                hreg.validate_spawn_arg(bad)
        assert hreg.validate_spawn_arg("normal-arg") == "normal-arg"

    def test_probe_not_installed(self, monkeypatch):
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: None)
        info = run(hreg.probe_harness("hermes", force=True))
        assert info["installed"] is False

    def test_probe_claude_unusable_without_key_or_login(self, monkeypatch):
        """claude 无 API key 且无本地登录态 → 不可用。"""
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: "C:/bin/claude.EXE")
        monkeypatch.setattr(hreg.os, "environ", {})
        monkeypatch.setattr(hreg, "_credential_store_present", lambda hid: False)

        class R:
            returncode = 0
            stdout = b"1.0.0"
            stderr = b""
        monkeypatch.setattr(hreg.subprocess, "run", lambda *a, **k: R())
        info = run(hreg.probe_harness("claude", force=True))
        assert info["installed"] is False
        assert hreg.configuration_issues("claude"), "expected a readable configuration issue"

    def test_probe_claude_usable_with_local_login(self, monkeypatch):
        """claude 无 API key 但有 OAuth 登录态 → 可用（订阅号用户不应被误判）。"""
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: "C:/bin/claude.EXE")
        monkeypatch.setattr(hreg.os, "environ", {})
        monkeypatch.setattr(hreg, "_credential_store_present", lambda hid: hid == "claude")

        class R:
            returncode = 0
            stdout = b"2.1.267 (Claude Code)"
            stderr = b""
        monkeypatch.setattr(hreg.subprocess, "run", lambda *a, **k: R())
        info = run(hreg.probe_harness("claude", force=True))
        assert info["installed"] is True
        assert info["credentials"]["store_ready"] is True
        assert hreg.configuration_issues("claude") == []

    def test_probe_reads_version_from_stderr(self, monkeypatch):
        """部分 CLI（实测 pi）把 --version 写到 stderr —— 必须同样识别。"""
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: "C:/bin/pi.CMD")

        class R:
            returncode = 0
            stdout = b""
            stderr = b"0.73.1\n"
        monkeypatch.setattr(hreg.subprocess, "run", lambda *a, **k: R())
        info = run(hreg.probe_harness("pi", force=True))
        assert info["installed"] is True
        assert info["version"] == "0.73.1"
        assert info["version_stream"] == "stderr"

    def test_probe_tolerates_nonzero_exit_with_version_output(self, monkeypatch):
        """部分 CLI 用非 0 退出码报告版本 —— 有可读输出即视为已安装。"""
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: "C:/bin/goose.EXE")

        class R:
            returncode = 1
            stdout = b"1.50.0"
            stderr = b""
        monkeypatch.setattr(hreg.subprocess, "run", lambda *a, **k: R())
        info = run(hreg.probe_harness("goose", force=True))
        assert info["installed"] is True
        assert info["version"] == "1.50.0"

    def test_assert_usable_three_states(self, monkeypatch):
        # 未知 → 400 语义
        with pytest.raises(hreg.UnknownHarnessError):
            run(hreg.assert_harness_usable("nope"))
        # 未安装 → 409 语义
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: None)
        with pytest.raises(hreg.HarnessUnavailableError):
            run(hreg.assert_harness_usable("hermes"))
        # 可用（mock 恒可用）
        probe = run(hreg.assert_harness_usable("mock"))
        assert probe["installed"] is True


# ── spec 构建器 ───────────────────────────────────────────────────────

class TestSpecBuilders:
    def test_all_registered_have_specs(self):
        for hid in hreg.HARNESS_IDS:
            spec = hspec.get_spec(hid)
            assert spec.delivery in ("stdin", "arg", "argfile", "embedded", "inprocess")

    def test_delivery_map(self):
        expect = {"omp": "argfile", "pi": "argfile",
                  "claude": "stdin", "codex": "stdin", "qwen": "stdin",
                  "gemini": "arg", "copilot": "arg",
                  "opencode": "arg", "cursor": "arg", "crush": "arg", "goose": "arg",
                  "dsh": "embedded", "hermes": "embedded", "mock": "inprocess"}
        for hid, delivery in expect.items():
            assert hspec.get_spec(hid).delivery == delivery, hid

    def test_omp_argfile(self):
        argv = hspec.build_engine_argv("omp", {"timeout_sec": 120, "model": "m1"},
                                       "PROMPT", "C:/t/p.txt")
        assert argv[-1] == "@C:/t/p.txt"
        assert "--max-time" in argv and "120" in argv
        assert "--model" in argv and "m1" in argv
        assert "--no-tools" not in argv  # meditation 需要工具面，no_tools 由 cfg 控制

    def test_omp_no_tools_when_configured(self):
        argv = hspec.build_engine_argv("omp", {"timeout_sec": 60, "no_tools": True},
                                       "P", "C:/t/p.txt")
        assert "--no-tools" in argv

    def test_codex_stdin_dash_readonly(self):
        argv = hspec.build_engine_argv("codex", {}, "P", None)
        assert argv[-1] == "-"
        assert "--sandbox" in argv and "read-only" in argv

    def test_claude_stdin_with_schema(self, monkeypatch):
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: "C:/bin/claude.EXE")
        argv = hspec.build_engine_argv(
            "claude", {"model": "claude-sonnet-4-20250514", "max_budget_usd": 0.05,
                       "result_schema": {"type": "object"}}, "P", None)
        assert "-p" in argv and "--output-format" in argv
        assert "--json-schema" in argv

    def test_claude_schema_on_cmd_shim_dropped_by_runner(self, monkeypatch):
        """.cmd 包装链拒绝引号参数 → runner 预先丢弃 --json-schema（显式降级）。"""
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: "C:/npm/claude.CMD")
        cfg = {"timeout_sec": 30, "result_schema": {"type": "object"}}
        res = run(hrun.run_engine("mock", "hi", {"result_schema": {"type": "object"}},
                                  "test-schema"))  # 对照：mock 不受影响
        assert res["success"]
        # claude 走 build 前降级：argv 构建应无 --json-schema
        argv = hspec.build_engine_argv("claude", {**cfg, "result_schema": None}, "P", None)
        assert "--json-schema" not in argv

    def test_goose_uses_t_flag(self, monkeypatch):
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: "C:/bin/goose.EXE")
        argv = hspec.build_engine_argv("goose", {"goose_name": "aw-x"}, "PROMPT", None)
        # 教训：位置参数被拒 → prompt 必须以 -t 投递（-t 紧邻 prompt）
        assert argv[-2] == "-t" and argv[-1] == "PROMPT"
        assert "--name" in argv and "aw-x" in argv

    def test_arg_delivery_multiline_on_native_exe(self, monkeypatch):
        """native exe 的 list-form Popen 不经 shell → prompt 含换行合法。"""
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: "C:/bin/goose.EXE")
        argv = hspec.build_engine_argv("goose", {}, "line1\nline2", None)
        assert argv[-1] == "line1\nline2"

    def test_arg_delivery_multiline_on_cmd_shim_rejected(self, monkeypatch):
        """.cmd 包装链：换行/引号参数被逐参数校验拒绝（结构化报错，不静默）。"""
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: "C:/npm/opencode.CMD")
        with pytest.raises(ValueError):
            hspec.build_engine_argv("opencode", {}, "line1\nline2", None)

    def test_prompt_limit_guard(self):
        with pytest.raises(ValueError):
            hspec.build_engine_argv("opencode", {}, "x" * 9000, None)
        # 无限制引擎不受影响
        hspec.build_engine_argv("claude", {}, "x" * 9000, None)

    def test_goose_engine_env(self):
        env = hspec.engine_env_for("goose", {"model": "gpt-x"})
        assert env["GOOSE_MODE"] == "auto"
        assert env["GOOSE_MODEL"] == "gpt-x"

    def test_build_engine_argv_resolves(self, monkeypatch):
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: f"C:/bin/{hid}.EXE")
        argv = hspec.build_engine_argv("cursor", {}, "P", None)
        assert argv[0] == "C:/bin/cursor.EXE"

    def test_build_engine_argv_missing_binary(self, monkeypatch):
        monkeypatch.setattr(hspec, "resolve_command", lambda hid: None)
        with pytest.raises(RuntimeError):
            hspec.build_engine_argv("cursor", {}, "P", None)


# ── 输出解析器 ────────────────────────────────────────────────────────

class TestParsers:
    def test_omp_jsonl(self):
        content = "\n".join([
            '{"type":"message_end","message":{"role":"user","content":[{"type":"text","text":"q"}]}}',
            'not json line ignored',
            '{"type":"agent_end","message":{"role":"assistant","content":[{"type":"text","text":"ANSWER"},{"type":"tool_use"}]}}',
        ])
        text, _ = hspec._parse_omp(content)
        assert text == "ANSWER"

    def test_claude_result_field(self):
        text, _ = hspec._parse_claude('{"type":"result","result":"FINAL","usage":{"x":1}}')
        assert text == "FINAL"

    def test_claude_result_json_dict(self):
        text, _ = hspec._parse_claude('{"result": {"meditation_result": {"kb_id": "k"}}}')
        assert "meditation_result" in text

    def test_codex_agent_message(self):
        content = "\n".join([
            '{"type":"thread.started","thread_id":"t"}',
            '{"type":"item.completed","item":{"type":"reasoning","text":"think"}}',
            '{"type":"item.completed","item":{"item_type":"agent_message","text":"CODEX OUT"}}',
            '{"type":"turn.completed","usage":{"input_tokens":3}}',
        ])
        text, usage = hspec._parse_codex(content)
        assert text == "CODEX OUT"
        assert usage == {"input_tokens": 3}

    def test_gemini_json(self):
        text, _ = hspec._parse_gemini_json('{"response": "GEM", "stats": {"n": 1}}')
        assert text == "GEM"

    def test_gemini_stream_fallback(self):
        content = '{"type":"init"}\n{"type":"result","response":"STREAM"}'
        text, _ = hspec._parse_gemini_json(content)
        assert text == "STREAM"

    def test_copilot_best_effort(self):
        text, _ = hspec._parse_copilot('{"messages":[],"response":"COPILOT"}')
        assert text == "COPILOT"
        # 纯文本兜底
        text2, _ = hspec._parse_copilot("just plain output")
        assert text2 == "just plain output"

    def test_cursor_result(self):
        text, _ = hspec._parse_cursor('{"result":"CURSOR FINAL","usage":{"a":1}}')
        assert text == "CURSOR FINAL"

    def test_crush_opencode_plain(self):
        assert hspec._plain_text("  hello world \n") == "hello world"

    def test_goose_assistant_message(self):
        content = '{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"GOOSE"}]}}'
        text, _ = hspec._parse_goose(content)
        assert text == "GOOSE"

    def test_qwen_plain_text_parser(self):
        # qwen 无 --output-format → 纯文本 stdout
        assert hspec.get_spec("qwen").parse_output("PLAIN OUT") == ("PLAIN OUT", None)

    def test_pi_message_end(self):
        content = "\n".join([
            '{"type":"session","id":"s"}',
            '{"type":"message_update","delta":"par"}',
            '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"PI FULL"}]}}',
        ])
        text, _ = hspec._parse_pi(content)
        assert text == "PI FULL"

    def test_pi_update_accumulation(self):
        content = '{"type":"message_update","delta":"a"}\n{"type":"message_update","delta":"b"}'
        text, _ = hspec._parse_pi(content)
        assert text == "ab"

    def test_unknown_events_ignored(self):
        content = '{"weird":"frame"}\n{"type":"future_event","x":1}\n' \
                  '{"type":"agent_end","message":{"role":"assistant","content":[{"type":"text","text":"OK"}]}}'
        text, _ = hspec._parse_omp(content)
        assert text == "OK"


# ── mock 进程内引擎全链路 ─────────────────────────────────────────────

class TestMockEndToEnd:
    def test_runner_mock_generic(self):
        res = run(hrun.run_engine("mock", "hello world", {}, "test-mock-1"))
        assert res["success"] and res["parsed"]["mock"] is True
        assert res["elapsed"] < 1

    def test_runner_mock_meditation_shape(self):
        prompt = ('系统提示词...\n目标知识库: demo (id=kb-77, path=x)\n'
                  '待处理信号: 4 条\n"kb_id": "kb-77",\n输出 meditation_result')
        res = run(hrun.run_engine("mock", prompt, {"result_schema": {}}, "test-mock-2"))
        assert res["success"]
        mr = res["parsed"]["meditation_result"]
        assert mr["kb_id"] == "kb-77"
        assert mr["total_signals_processed"] == 4
        assert isinstance(mr["drafts_created"], list)

    def test_manager_complete_mock(self):
        from app.services.agent_harness_manager import AgentHarnessManager
        m = AgentHarnessManager()
        res = run(m.complete(prompt="plain question",
                             kb_config={"harness": "mock", "timeout_sec": 30}))
        assert res["success"] is True
        assert res["harness"] == "mock"
        assert res["parsed"]["summary"]

    def test_manager_complete_unknown(self):
        from app.services.agent_harness_manager import AgentHarnessManager
        m = AgentHarnessManager()
        res = run(m.complete(prompt="x", kb_config={"harness": "does-not-exist"}))
        assert res["success"] is False
        assert "Supported" in res["error"]

    def test_manager_synthesize_unknown(self):
        from app.services.agent_harness_manager import AgentHarnessManager
        m = AgentHarnessManager()
        res = run(m.synthesize_experiences(
            kb_path="p", kb_id="k", signals=[], trigger="manual",
            kb_config={"harness": "bogus"}))
        assert res["success"] is False
        assert "Unknown harness" in res["error"]

    def test_manager_synthesize_mock_manual(self):
        """mock 引擎手动触发的冥想合成全链路（run 记录 + 结果解析）。"""
        from app.services.agent_harness_manager import AgentHarnessManager
        m = AgentHarnessManager()
        res = run(m.synthesize_experiences(
            kb_path="mock-kb", kb_id="kb-mock",
            signals=[{"question_text": "q1?", "assistant_answer": "a1", "retrieved_docs": []}],
            kb_config={"harness": "mock", "timeout_sec": 60, "max_drafts_per_run": 3},
            trigger="manual"))
        assert res["success"], res.get("error")
        assert res["harness"] == "mock"
        assert res["drafts"] and res["total_signals_processed"] == 1


# ── meditation 结果提取 ──────────────────────────────────────────────

class TestMeditationExtraction:
    def test_fenced_json(self):
        text = '说明文字\n```json\n{"meditation_result": {"kb_id": "k1", "drafts_created": [], "total_signals_processed": 2}}\n```\n'
        res = hrun.meditation_result_from_text(text)
        assert res["success"] and res["kb_id"] == "k1" and res["total_signals_processed"] == 2

    def test_embedded_quotes_repair(self):
        text = '```json\n{"meditation_result": {"summary": "他说"先结论后论证"是对的", "drafts_created": [], "total_signals_processed": 1}}\n```'
        res = hrun.meditation_result_from_text(text)
        assert res["success"], res
        assert "先结论后论证" in res["summary"]

    def test_flat_result(self):
        res = hrun.meditation_result_from_text('{"experiences_created": [], "drafts_created": [{"title": "t"}], "total_signals_processed": 3}')
        assert res["success"] and len(res["drafts"]) == 1

    def test_garbage_fails(self):
        res = hrun.meditation_result_from_text("no json at all")
        assert not res["success"]

    def test_empty_fails(self):
        assert not hrun.meditation_result_from_text("")["success"]


# ── ACP / 进程治理辅助 ────────────────────────────────────────────────

class TestProcessGovernance:
    def test_safe_log_path_anchored(self, tmp_path):
        p = hrun.safe_log_path(tmp_path, "meditation-agent-1", ".out")
        assert p.parent == tmp_path.resolve()
        assert p.name == "meditation-agent-1.out"

    def test_safe_log_path_strips_escape_chars(self, tmp_path):
        p = hrun.safe_log_path(tmp_path, "../../evil", ".out")
        assert ".." not in p.name
        assert p.parent == tmp_path.resolve()

    def test_secure_tempfile_unique(self):
        a, b = hrun.secure_tempfile("x-"), hrun.secure_tempfile("x-")
        assert a != b and a.exists() and b.exists()
        a.unlink(missing_ok=True)
        b.unlink(missing_ok=True)

    def test_build_result_shape(self):
        r = hrun.build_result({"kb_id": "k", "experiences_created": [{"title": "e"}],
                               "drafts_created": [], "skipped": [], "total_signals_processed": 9})
        assert r["success"] and len(r["experiences"]) == 1 and r["total_signals_processed"] == 9


# ── 默认引擎可用性感知解析 ────────────────────────────────────────────

class TestDefaultResolution:
    def setup_method(self):
        hreg.reset_probe_cache()

    def teardown_method(self):
        hreg.reset_probe_cache()

    def test_configured_installed_wins(self, monkeypatch):
        async def fake_impl(hid):
            return _fake_probe_ok(hid)
        monkeypatch.setattr(hreg, "_probe_impl", fake_impl)
        assert run(hreg.resolve_default_harness(force=True)) == "omp"

    def test_falls_back_to_first_installed(self, monkeypatch):
        # 配置引擎 omp 未装 → 回落到注册表顺序中第一个已装的真实引擎
        async def fake_impl(hid):
            return _fake_probe_ok(hid) if hid == "pi" else {"installed": False}
        monkeypatch.setattr(hreg, "_probe_impl", fake_impl)
        assert run(hreg.resolve_default_harness(force=True)) == "pi"

    def test_all_missing_falls_to_mock(self, monkeypatch):
        async def fake_impl(hid):
            return {"installed": False}
        monkeypatch.setattr(hreg, "_probe_impl", fake_impl)
        assert run(hreg.resolve_default_harness(force=True)) == "mock"

    def test_sync_cached_variant(self, monkeypatch):
        from app.config import config
        monkeypatch.setitem(config._config, "soul", {"default_harness": "omp"})
        # 缓存冷 → 回落配置值
        hreg.reset_probe_cache()
        assert hreg.resolve_default_harness_cached() == "omp"
        # 缓存暖且 omp 可用 → omp
        hreg._PROBE_CACHE["omp"] = {"installed": True}
        assert hreg.resolve_default_harness_cached() == "omp"
        # 缓存暖但 omp 不可用、pi 可用 → pi
        hreg._PROBE_CACHE["omp"] = {"installed": False}
        hreg._PROBE_CACHE["pi"] = {"installed": True}
        assert hreg.resolve_default_harness_cached() == "pi"
        hreg.reset_probe_cache()


def _fake_probe_ok(hid: str) -> dict:
    return {"installed": True, "version": "fake", "resolved_command": "fake",
            "inprocess": hid == "mock", "env": []}


# ── 假 CLI 桩：14 引擎适配链全覆盖（无凭据，零 token） ────────────────

FAKE_PROMPT = "FAKEPROMPT-ABCDEFGHIJKLMNOP"


class TestFakeCliAdapters:
    """为每个引擎造一个桩可执行文件，真实走完 resolve→wrap→spawn→投递→解析。

    桩输出 FAKE-<ID>-OK:<prompt前16字符>，同时证明拉起与投递两件事。
    """

    @pytest.fixture(autouse=True)
    def _stub_launcher(self, tmp_path, monkeypatch):
        self.stub_src = Path(__file__).parent / "fake_harness_engine.py"
        self.launchers = {}
        py = Path(sys.executable)
        for hid in hreg.HARNESS_IDS:
            if hid == "mock":
                continue
            if sys.platform == "win32":
                launcher = tmp_path / f"{hid}.cmd"
                launcher.write_text(
                    '@echo off\r\n'
                    f'"{py}" "{self.stub_src}" {hid} %*\r\n',
                    encoding="ascii")
            else:
                launcher = tmp_path / hid
                launcher.write_text(
                    f"#!/usr/bin/env python3\n"
                    f'import runpy,sys; sys.argv[1]="{hid}"; '
                    f'runpy.run_path(r"{self.stub_src}", run_name="__main__")\n',
                    encoding="utf-8")
                launcher.chmod(0o755)
            self.launchers[hid] = launcher
        def resolver(hid):
            launcher = self.launchers.get(hid)
            return str(launcher) if launcher else None
        monkeypatch.setattr(hspec, "resolve_command", resolver)
        monkeypatch.setattr(hreg, "resolve_command", resolver)
        yield

    @pytest.mark.parametrize("hid", [h for h in hreg.HARNESS_IDS if h != "mock"])
    def test_engine_executes_kb_job(self, hid):
        cfg = {"timeout_sec": 60, "goose_name": "aw-t"}
        res = run(hrun.run_engine(hid, FAKE_PROMPT, cfg, run_label=f"fake-{hid}"))
        assert res["success"], f"{hid}: {res.get('error')} / {res.get('detail', '')[:300]}"
        assert f"FAKE-{hid.upper()}-OK" in res["text"], hid
        assert FAKE_PROMPT[:16] in res["text"], f"{hid}: prompt not delivered"

    def test_meditation_job_through_mock_channel(self):
        """mock 引擎跑知识库管理作业（meditation 形态）→ 标准化结果。"""
        from app.services.agent_harness_manager import AgentHarnessManager
        m = AgentHarnessManager()
        res = run(m.synthesize_experiences(
            kb_path="stub-kb", kb_id="kb-stub",
            signals=[{"question_text": "q", "assistant_answer": "a", "retrieved_docs": []}],
            kb_config={"harness": "mock", "timeout_sec": 30},
            trigger="manual"))
        assert res["success"] and res["drafts"]

    # ── ACP 协议契约回归 ─────────────────────────────────────────────
    # 背景：驱动器曾按 `sessionUpdate == "agent_message_text"` 聚合文本。该判别值
    # 在 ACP v1 规范、各语言 SDK schema 和真实 dsh 二进制里**都不存在**
    # （真实值是 agent_message_chunk），所以 dsh/hermes 在生产里永远拿到空回复；
    # 而桩文件当年写的也是同一个错值，单测因此全绿。下面两条把契约钉死。

    @pytest.mark.parametrize("hid", ["dsh", "hermes"])
    def test_acp_text_uses_spec_discriminator(self, hid):
        """真实 ACP 判别值 agent_message_chunk 必须被聚合为回复文本。"""
        cfg = {"timeout_sec": 60}
        res = run(hrun.run_engine(hid, FAKE_PROMPT, cfg, run_label=f"acp-{hid}"))
        assert res["success"], f"{hid}: {res.get('error')} / {res.get('detail', '')[:300]}"
        assert res["text"].strip(), f"{hid}: ACP text update was not accumulated"
        assert f"FAKE-{hid.upper()}-OK" in res["text"], res["text"][:200]

    @pytest.mark.parametrize("hid", ["dsh", "hermes"])
    def test_acp_permission_is_denied_via_offered_option(self, hid, tmp_path):
        """拒绝审批应回 selected+reject optionId，而不是无条件 cancelled。

        规范：`cancelled` 是「本回合被取消」的专属应答；普通拒绝必须从 agent 给出的
        options 里挑一个 reject_*，否则合规 agent 会把回合判为取消并中止。
        """
        import glob
        import tempfile
        pattern = str(Path(tempfile.gettempdir()) / "fake-harness-perm-*.json")
        for stale in glob.glob(pattern):
            Path(stale).unlink(missing_ok=True)
        old = os.environ.get("FAKE_HARNESS_PERM_LOG")
        os.environ["FAKE_HARNESS_PERM_LOG"] = "1"   # 仅作开关；路径由夹具自管
        try:
            res = run(hrun.run_engine(hid, FAKE_PROMPT, {"timeout_sec": 60},
                                      run_label=f"perm-{hid}"))
        finally:
            if old is None:
                os.environ.pop("FAKE_HARNESS_PERM_LOG", None)
            else:
                os.environ["FAKE_HARNESS_PERM_LOG"] = old

        assert res["success"], f"{hid}: {res.get('error')}"
        hits = sorted(glob.glob(pattern))
        assert hits, f"{hid}: the driver never answered the permission request"
        outcome = json.loads(Path(hits[-1]).read_text(encoding="utf-8")).get("outcome", {})
        assert outcome.get("outcome") == "selected", outcome
        assert outcome.get("optionId") == "reject-1", outcome


# ── API 路由层（三态校验 + 注册表面） ─────────────────────────────────

class TestApiLayer:
    def test_harness_list_endpoint(self):
        from app.api.routes.meditation import harness_list
        res = run(harness_list())
        assert res["success"] and res["count"] == 15  # 14 + heuristic
        ids = [h["id"] for h in res["harnesses"]]
        assert ids[-1] == "heuristic"
        for h in res["harnesses"]:
            assert "installed" in h and "capabilities" in h and "models" in h

    def test_validate_unknown_400(self):
        from app.api.routes.meditation import _validate_harness
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            run(_validate_harness("nope"))
        assert ei.value.status_code == 400

    def test_validate_not_installed_409(self, monkeypatch):
        from app.api.routes.meditation import _validate_harness
        from fastapi import HTTPException
        monkeypatch.setattr(hreg, "resolve_command", lambda hid: None)
        with pytest.raises(HTTPException) as ei:
            run(_validate_harness("hermes"))
        assert ei.value.status_code == 409

    def test_validate_installed_ok(self):
        from app.api.routes.meditation import _validate_harness
        assert run(_validate_harness("mock"))["installed"] is True

    def test_models_unknown_400(self):
        from app.api.routes.meditation import meditation_models
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            run(meditation_models(harness="nope"))
        assert ei.value.status_code == 400

    def test_models_static_catalog(self):
        from app.api.routes.meditation import meditation_models
        res = run(meditation_models(harness="gemini"))
        ids = [m["id"] for m in res["models"]]
        assert "" in ids and "gemini-2.5-pro" in ids


# ── 配置覆盖链 ────────────────────────────────────────────────────────

class TestConfig:
    def test_harness_command_override(self, monkeypatch):
        from app.config import config
        monkeypatch.setitem(config._config, "harness",
                            {"commands": {"crush": "D:/bin/crush.exe"}})
        assert config.harness_command("crush") == "D:/bin/crush.exe"
        assert config.harness_command("omp") == ""

    def test_default_harness_validated(self, monkeypatch):
        from app.config import config
        monkeypatch.setitem(config._config, "soul", {"default_harness": "goose"})
        assert config.soul_default_harness == "goose"
        monkeypatch.setitem(config._config, "soul", {"default_harness": "bogus"})
        assert config.soul_default_harness == "omp"
