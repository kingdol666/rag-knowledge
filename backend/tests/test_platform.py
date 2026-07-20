"""跨平台逻辑回归测试 — mock 驱动，三平台（Win/Linux/Mac）均可跑。

覆盖跨平台改造（B1-B5）的平台分支逻辑，无需真实 GPU/MinerU：
  - embedding_device 的 cuda > mps > cpu 优先级（B2）
  - _resolve_base_url 的 HF_ENDPOINT 镜像切换（B3）
  - _linux_set_pdeathsig 全平台 import-safe + 非 Linux no-op（B1）

CI 在 ubuntu/macos/windows matrix 跑此文件，验证平台分支逻辑一致。
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


# ── B2: embedding_device 优先级 cuda > mps > cpu ───────────────────
class TestEmbeddingDevice:
    def _setup(self, monkeypatch, device_yaml, cuda, mps):
        from app.config import config

        monkeypatch.setitem(config._config, "embedding", {"device": device_yaml})
        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = cuda
        fake_torch.backends.mps.is_available.return_value = mps
        monkeypatch.setitem(sys.modules, "torch", fake_torch)
        return config

    def test_explicit_cuda_respected(self, monkeypatch):
        cfg = self._setup(monkeypatch, "cuda", cuda=False, mps=True)
        assert cfg.embedding_device == "cuda"

    def test_explicit_cpu_respected(self, monkeypatch):
        cfg = self._setup(monkeypatch, "cpu", cuda=True, mps=True)
        assert cfg.embedding_device == "cpu"

    def test_auto_cuda_priority_over_mps(self, monkeypatch):
        cfg = self._setup(monkeypatch, None, cuda=True, mps=True)
        assert cfg.embedding_device == "cuda"

    def test_auto_mps_when_no_cuda(self, monkeypatch):
        cfg = self._setup(monkeypatch, None, cuda=False, mps=True)
        assert cfg.embedding_device == "mps"

    def test_auto_cpu_when_no_gpu(self, monkeypatch):
        cfg = self._setup(monkeypatch, None, cuda=False, mps=False)
        assert cfg.embedding_device == "cpu"

    def test_auto_keyword_triggers_detection(self, monkeypatch):
        cfg = self._setup(monkeypatch, "auto", cuda=False, mps=True)
        assert cfg.embedding_device == "mps"


# ── B3: HF_ENDPOINT 镜像切换 ───────────────────────────────────────
class TestResolveBaseUrl:
    def test_default_mirror_china(self, monkeypatch):
        monkeypatch.delenv("HF_ENDPOINT", raising=False)
        from app.utils.download_model import _resolve_base_url

        url = _resolve_base_url("BAAI/bge-m3")
        assert "hf-mirror.com" in url
        assert "BAAI/bge-m3/resolve/main" in url

    def test_hf_override_for_overseas(self, monkeypatch):
        monkeypatch.setenv("HF_ENDPOINT", "https://huggingface.co")
        from app.utils.download_model import _resolve_base_url

        url = _resolve_base_url("BAAI/bge-m3")
        assert "huggingface.co" in url
        assert "hf-mirror.com" not in url

    def test_custom_endpoint(self, monkeypatch):
        monkeypatch.setenv("HF_ENDPOINT", "https://my.mirror.cn")
        from app.utils.download_model import _resolve_base_url

        assert "my.mirror.cn" in _resolve_base_url("X/Y")


# ── B1: prctl helper 全平台 import-safe ────────────────────────────
class TestLinuxPdeathsig:
    def test_importable_on_all_platforms(self):
        # B1 在 win32 分支也加了 no-op stub，确保 _linux_set_pdeathsig 全平台可 import
        from app.utils.mineru_manager import _linux_set_pdeathsig

        assert callable(_linux_set_pdeathsig)

    def test_call_is_safe_on_any_platform(self):
        # 无论真实平台（Linux 实际调 prctl best-effort；Win/Mac no-op），都不应抛异常
        from app.utils.mineru_manager import _linux_set_pdeathsig

        _linux_set_pdeathsig()  # 无副作用、无异常


# ── B4: MinerU model_source 从 config 读取（mock config） ──────────
class TestMineruModelSource:
    def test_reads_from_config_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("MINERU_MODEL_SOURCE", raising=False)
        from app.config import config

        monkeypatch.setitem(
            config._config,
            "mineru",
            {"model_source": "huggingface", "enabled": True, "host": "127.0.0.1"},
        )
        # 验证 config.mineru 从 _config dict 正确读取（B4 的 model_source 读取基础）
        assert config.mineru.get("model_source") == "huggingface"
