"""SOUL 模块最小自动化测试(5.1)— 纯函数级,不依赖外部服务。

覆盖: complete() 解析助手、config 新字段与 known_fields 门、soul_config 默认值、
q_hash 语义。集成/端到端由 §6 验收清单覆盖。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.agent_harness_manager import agent_harness
from app.services.kb_meditation_config import DEFAULT_MEDITATION_CONFIG, _update_meditation_config_locked
from app.services import soul_config
from app.services.soul_learn import q_hash


# ── complete() 解析助手 ─────────────────────────────────────────────────

class TestExtractJsonBlock:
    def test_fenced_json(self):
        text = '```json\n{"a": 1}\n```'
        assert agent_harness._extract_json_block(text) == {"a": 1}

    def test_prose_with_trailing_json(self):
        text = '好的,结果是:\n{"ranked": [{"kb_id": "soul-x", "score": 0.8, "reason": "匹配"}]}'
        parsed = agent_harness._extract_json_block(text)
        assert parsed["ranked"][0]["kb_id"] == "soul-x"

    def test_malformed_returns_none(self):
        assert agent_harness._extract_json_block("no json here { broken") is None

    def test_string_inside_json_not_confused(self):
        text = '{"a": "} not a close", "b": [1, 2]} tail'
        parsed = agent_harness._extract_json_block(text)
        assert parsed == {"a": "} not a close", "b": [1, 2]}


class TestParseCompleteLog:
    def _write_log(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "run.log"
        p.write_text(content, encoding="utf-8")
        return p

    def test_omp_event_extraction(self, tmp_path):
        log = self._write_log(tmp_path, (
            '{"type":"agent_start"}\n'
            '{"type":"message_end","message":{"role":"assistant","content":'
            '[{"type":"text","text":"{\\"answer\\": 42}"}]}}\n'
        ))
        text, parsed = agent_harness._parse_complete_log(log, "omp", None)
        assert parsed == {"answer": 42}

    def test_claude_result_field(self, tmp_path):
        log = self._write_log(tmp_path, (
            '{"type":"result","subtype":"success","result":"{\\"ok\\": true}"}\n'
        ))
        text, parsed = agent_harness._parse_complete_log(log, "claude", {"ok": "boolean"})
        assert parsed == {"ok": True}

    def test_missing_log_returns_empty(self, tmp_path):
        text, parsed = agent_harness._parse_complete_log(tmp_path / "nope.log", "omp", None)
        assert text == "" and parsed is None


# ── M0.3 config 扩展 ────────────────────────────────────────────────────

class TestMeditationConfigExtension:
    def test_new_fields_in_defaults(self):
        assert DEFAULT_MEDITATION_CONFIG["meditation_mode"] == "experience"
        assert DEFAULT_MEDITATION_CONFIG["max_questions_per_run"] == 10
        assert DEFAULT_MEDITATION_CONFIG["min_pas_auto_approve"] == 4.0

    def test_known_fields_gate_accepts_new_fields(self, tmp_path, monkeypatch):
        """M0.3 后 experience_meditation_config_update 传 meditation_mode 不再被丢弃。"""
        yaml_path = tmp_path / ".knowledge-base.yml"
        yaml_path.write_text("knowledge_base:\n  metadata: {}\n", encoding="utf-8")
        r = _update_meditation_config_locked("soul-test", yaml_path, {
            "meditation_mode": "soul", "max_budget_usd": 0.15})
        assert r.get("success") is True
        import yaml
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        meta = data["knowledge_base"]["metadata"]["meditation"]
        assert meta["meditation_mode"] == "soul"
        assert meta["max_budget_usd"] == 0.15

    def test_unknown_field_still_dropped(self, tmp_path):
        yaml_path = tmp_path / ".knowledge-base.yml"
        yaml_path.write_text("knowledge_base:\n  metadata: {}\n", encoding="utf-8")
        r = _update_meditation_config_locked("soul-test", yaml_path, {"not_a_field": 1})
        assert r.get("success") is True
        import yaml
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "not_a_field" not in data["knowledge_base"]["metadata"]["meditation"]


# ── soul_config 基础 ────────────────────────────────────────────────────

class TestSoulConfigBasics:
    def test_defaults(self):
        cfg = soul_config.SoulConfig()
        assert cfg.kb_scope == [] and cfg.is_template is False
        assert cfg.route_weight == 1.0

    def test_scope_hash_deterministic_and_order_insensitive(self):
        a = soul_config.scope_hash(["kb-1", "kb-2"])
        b = soul_config.scope_hash(["kb-2", "kb-1"])
        c = soul_config.scope_hash(["kb-1", "kb-2"])
        assert a == b == c and len(a) == 64

    def test_constants(self):
        assert soul_config.SOUL_RETRIEVAL_SCORE_THRESHOLD == 0.5
        assert soul_config.SOUL_BUDGET_USD_PER_RUN == 0.15
        assert soul_config.ROUTE_CONFIDENCE_THRESHOLD == 0.6


# ── q_hash 语义(§11.8c) ────────────────────────────────────────────────

class TestQHash:
    def test_deterministic(self):
        assert q_hash("问题", "docs/a.md", "fact") == q_hash("问题", "docs/a.md", "fact")

    def test_sensitive_to_doc_and_type(self):
        assert q_hash("问题", "docs/a.md", "fact") != q_hash("问题", "docs/b.md", "fact")
        assert q_hash("问题", "docs/a.md", "fact") != q_hash("问题", "docs/a.md", "concept")

    def test_truncated_prefix(self):
        long_q = "x" * 500
        h = q_hash(long_q, "d.md", "fact")
        assert len(h) == 12
