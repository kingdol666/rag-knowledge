#!/usr/bin/env python3
"""
模型自动下载工具。

从 HuggingFace / hf-mirror 下载模型到项目级 models_cache/：
  - Embedding 模型（BAAI/bge-m3，~2.2GB）—— 向量检索必需

Embedding 用 requests + HTTP Range 断点续传（自管缓存结构，支持大文件进度）。
下载时禁用系统 HTTPS_PROXY（Clash 7890 会破坏 hf-mirror HTTPS）。
"""
from __future__ import annotations

import contextlib
import logging
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # backend/app/utils/download_model.py → rag-knowledge/
SHARED_CONFIG = PROJECT_ROOT / "config.yml"

# ── 专用 logger：只配置自身，不污染全局 logging ──────────────────
logger = logging.getLogger("download_model")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(stream=sys.stdout)
_handler.setFormatter(logging.Formatter("[download_model] %(levelname)s %(message)s"))
logger.addHandler(_handler)
logger.propagate = False  # 阻止冒泡到 root logger（避免污染 uvicorn/watchfiles 等其他 logger）

# BGE-M3 的所有文件列表（30 个文件 = 2.2GB）
# 基础 URL 由 _resolve_base_url() 从 HF_ENDPOINT 派生（默认 hf-mirror.com）
FILES = [
    ".gitattributes",
    "1_Pooling/config.json",
    "README.md",
    "colbert_linear.pt",
    "config.json",
    "config_sentence_transformers.json",
    "imgs/.DS_Store",
    "imgs/bm25.jpg",
    "imgs/long.jpg",
    "imgs/miracl.jpg",
    "imgs/mkqa.jpg",
    "imgs/nqa.jpg",
    "imgs/others.webp",
    "long.jpg",
    "modules.json",
    "onnx/config.json",
    "onnx/Constant_7_attr__value",
    "onnx/model.onnx",
    "onnx/model.onnx_data",
    "onnx/sentencepiece.bpe.model",
    "onnx/special_tokens_map.json",
    "onnx/tokenizer.json",
    "onnx/tokenizer_config.json",
    "pytorch_model.bin",
    "sentence_bert_config.json",
    "sentencepiece.bpe.model",
    "sparse_linear.pt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
]

SNAPSHOT_ID = "5617a9f61b028005a4858fdac845db406aefb181"
MIN_FILES = 17
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for efficient streaming
TIMEOUT = (30, 600)  # (connect timeout, read timeout) — 10 min between chunks

GRADE = "============================================================"
WARNING_MSG = f"""
{GRADE}
  WARNING: Embedding model NOT available
  Vector search -> BM25 fallback
{GRADE}
"""


def _load_embedding_config() -> dict:
    import yaml
    if not SHARED_CONFIG.exists():
        return {"model_name": "BAAI/bge-m3", "cache_dir": "./models_cache"}
    with open(SHARED_CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    e = cfg.get("embedding", {})
    return {"model_name": e.get("model_name", "BAAI/bge-m3"),
            "cache_dir": e.get("cache_dir", "./models_cache")}


@contextlib.contextmanager
def _no_proxy():
    """临时清除 HTTPS_PROXY/HTTP_PROXY（Clash 7890 会破坏 hf-mirror HTTPS）。

    与 download_model 的 trust_env=False 策略一致：直连 hf-mirror 更稳定。
    """
    saved: dict[str, str] = {}
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        val = os.environ.pop(key, None)
        if val is not None:
            saved[key] = val
    os.environ["NO_PROXY"] = "*"
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    try:
        yield
    finally:
        os.environ.pop("NO_PROXY", None)
        for k, v in saved.items():
            os.environ[k] = v


def _abs_cache(raw: str) -> Path:
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def _resolve_base_url(model_name: str) -> str:
    """从 HF_ENDPOINT 派生下载 URL。默认 hf-mirror.com（中国区快）；海外设 HF_ENDPOINT=https://huggingface.co。"""
    endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")
    return f"{endpoint}/{model_name}/resolve/main"


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    else:
        return f"{b / (1024**3):.2f} GB"


def _download_file(session, url: str, dest: Path) -> bool:
    """下载单个文件，支持断点续传和进度显示。

    - 小文件 (< 10MB)：直接下载，静默
    - 大文件：显示进度百分比 + 速度
    - 断点续传：检测 .tmp 文件，使用 Range 头继续下载
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    # 完整文件已存在 → 跳过
    if dest.exists() and dest.stat().st_size > 0:
        return True

    tmp = Path(str(dest) + ".tmp")
    resumed_bytes = 0

    # 断点续传：检查是否有未完成的 .tmp
    if tmp.exists():
        resumed_bytes = tmp.stat().st_size
        if resumed_bytes > 0:
            logger.info("    Resuming from %s ...", _fmt_size(resumed_bytes))

    # 请求头
    headers = {}
    if resumed_bytes > 0:
        headers["Range"] = f"bytes={resumed_bytes}-"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 先发 HEAD 获取文件大小（仅首次）
            total_size = 0
            if attempt == 0 and resumed_bytes == 0:
                try:
                    h = session.head(url, timeout=TIMEOUT)
                    if "Content-Length" in h.headers:
                        total_size = int(h.headers["Content-Length"])
                except Exception:
                    pass

            # 流式下载
            resp = session.get(url, timeout=TIMEOUT, stream=True, headers=headers)

            if resp.status_code == 416:
                # Range Not Satisfiable — 文件已完整
                tmp.rename(dest)
                return True

            if resp.status_code not in (200, 206):
                logger.warning("    HTTP %d, retrying...", resp.status_code)
                time.sleep(2 ** attempt)
                continue

            # 如果服务器返回 Content-Range，取 total
            if "Content-Range" in resp.headers:
                # bytes X-Y/Z
                cr = resp.headers["Content-Range"]
                total_size = int(cr.split("/")[-1])
            elif "Content-Length" in resp.headers:
                total_size = resumed_bytes + int(resp.headers["Content-Length"])

            mode = "ab" if resumed_bytes > 0 else "wb"
            start_time = time.time()
            downloaded = resumed_bytes
            last_report = start_time
            last_bytes = resumed_bytes

            with open(tmp, mode) as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 每秒报告一次进度（仅大文件 > 10MB）
                        now = time.time()
                        if total_size > 10 * 1024 * 1024 and (now - last_report) >= 1.0:
                            pct = downloaded / total_size * 100
                            speed = (downloaded - last_bytes) / max(now - last_report, 0.01)
                            speed_str = _fmt_size(int(speed)) + "/s"
                            logger.info("    %5.1f%%  %s / %s  (%s)",
                                        pct, _fmt_size(downloaded),
                                        _fmt_size(total_size), speed_str)
                            last_report = now
                            last_bytes = downloaded

            # 下载完成，原子 rename
            tmp.rename(dest)

            elapsed = time.time() - start_time
            if total_size > 10 * 1024 * 1024:
                avg_speed = _fmt_size(int(downloaded / max(elapsed, 0.01))) + "/s"
                logger.info("    [OK] done  %s  (%s elapsed, avg %s)",
                            _fmt_size(downloaded),
                            _format_duration(elapsed), avg_speed)
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning("    Retry %d/%d in %ds: %s",
                               attempt + 1, max_retries, wait, _short_err(e))
                time.sleep(wait)
                # 更新 resume 位置
                if tmp.exists():
                    resumed_bytes = tmp.stat().st_size
                    headers["Range"] = f"bytes={resumed_bytes}-"
            else:
                raise

    return False


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s}s"


def _try_download_via_http(model_name: str, cache_dir: str) -> bool:
    """通过 HTTP 直接下载文件到正确的缓存结构。

    使用断点续传 + 大文件进度显示。不依赖 huggingface_hub API。
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    # 必须关闭 trust_env，防止系统 HTTPS_PROXY（如 Clash 7890）
    # 劫持 hf-mirror.com 的 HTTPS 请求导致 SSL 错误 / 超时
    session.trust_env = False
    retries = Retry(total=2, backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # 尝试多个镜像（从 HF_ENDPOINT 派生，默认 hf-mirror.com，fallback huggingface.co）
    base_url = _resolve_base_url(model_name)
    urls_to_try = [base_url]
    if "huggingface" not in base_url:
        urls_to_try.append(
            base_url.replace("hf-mirror.com", "huggingface.co"))

    hub_name = f"models--{model_name.replace('/', '--')}"
    hub_dir = Path(cache_dir) / "hub" / hub_name
    snap_dir = hub_dir / "snapshots" / SNAPSHOT_ID

    snap_dir.mkdir(parents=True, exist_ok=True)
    (hub_dir / "refs").mkdir(parents=True, exist_ok=True)
    (hub_dir / "blobs").mkdir(parents=True, exist_ok=True)
    (hub_dir / "refs" / "main").write_text(SNAPSHOT_ID)

    # 清理旧版破损 .tmp
    for stale in snap_dir.rglob("*.tmp"):
        stale.unlink(missing_ok=True)

    logger.info("Downloading %d files to %s ...", len(FILES), snap_dir)
    logger.info("Snapshot: %s", SNAPSHOT_ID)

    # 先统计已存在的文件数
    existing = sum(1 for f in FILES if (snap_dir / f).exists()
                   and (snap_dir / f).stat().st_size > 0)
    if existing > 0:
        logger.info("Already cached: %d/%d files", existing, len(FILES))

    success_count = existing
    # 只跳过已完整下载的文件，确保所有文件都尝试下载
    for base_url in urls_to_try:
        logger.info("Using mirror: %s", base_url)
        for i, filename in enumerate(FILES):
            url = f"{base_url}/{filename}"
            dest = snap_dir / filename

            # 跳过已存在的文件
            if dest.exists() and dest.stat().st_size > 0:
                continue

            logger.info("  [%d/%d] %s", i + 1, len(FILES), filename)

            try:
                _download_file(session, url, dest)
                success_count += 1
            except Exception as e:
                logger.warning("  [FAIL] %s -> %s", filename, _short_err(e))
                # 如果是关键大文件失败，尝试下一个镜像
                if filename in ("pytorch_model.bin", "onnx/model.onnx_data",
                                "onnx/model.onnx"):
                    break
        # 如果所有文件都下载成功了，退出镜像循环
        all_ok = all(
            (snap_dir / f).exists() and (snap_dir / f).stat().st_size > 0
            for f in FILES
        )
        if all_ok:
            break

    # 验证
    model_file = snap_dir / "pytorch_model.bin"
    if not model_file.exists():
        logger.error("pytorch_model.bin not downloaded!")
        return False

    model_size = model_file.stat().st_size
    if model_size < 1_000_000_000:
        logger.error("pytorch_model.bin too small: %s (should be ~2.2GB)", _fmt_size(model_size))
        return False

    # 检查关键文件
    missing = []
    for key_file in ["tokenizer.json", "config.json", "modules.json",
                     "sentencepiece.bpe.model", "sentence_bert_config.json"]:
        if not (snap_dir / key_file).exists():
            missing.append(key_file)
    if missing:
        logger.warning("Some files missing: %s - model may still work", missing)

    logger.info("Downloaded %d/%d files (model: %s)",
                success_count, len(FILES), _fmt_size(model_size))
    return True


def _model_files_ok(cache_dir: str, model_name: str) -> bool:
    """检查模型缓存是否完整。"""
    hub_dir = Path(cache_dir) / "hub" / f"models--{model_name.replace('/', '--')}"
    if not (hub_dir / "refs" / "main").exists():
        return False
    snap_id = (hub_dir / "refs" / "main").read_text().strip()
    snap = hub_dir / "snapshots" / snap_id
    model = snap / "pytorch_model.bin"
    if not model.exists() or model.stat().st_size < 1_000_000_000:
        return False
    for r in ["modules.json", "tokenizer.json", "config.json"]:
        if not (snap / r).exists():
            return False
    return True


def _short_err(e: Exception) -> str:
    return str(e).replace("\n", " ")[:120]


def ensure_model_downloaded(force: bool = False) -> bool:
    """主入口：检查并下载 Embedding 模型。

    Returns True=成功/已有缓存, False=下载失败。
    """
    cache_dir = _abs_cache(_load_embedding_config()["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Embedding 模型（向量检索必需）──────────────────────────
    emb_ok = _ensure_embedding_model(cache_dir, force)

    # Embedding 是硬依赖
    return bool(emb_ok)


def _ensure_embedding_model(cache_dir: Path, force: bool) -> bool:
    """下载 embedding 模型（BGE-M3）。"""
    cfg = _load_embedding_config()
    model_name = cfg["model_name"]

    logger.info(GRADE)
    logger.info("  Embedding Model Setup")
    logger.info("  Model : %s", model_name)
    logger.info("  Cache : %s", cache_dir)
    logger.info(GRADE)

    if force:
        hub = cache_dir / "hub" / f"models--{model_name.replace('/', '--')}"
        if hub.exists():
            shutil.rmtree(hub, ignore_errors=True)
            logger.info("Old embedding cache removed (--force)")

    if not force and _model_files_ok(str(cache_dir), model_name):
        logger.info("Embedding model already cached -> skip download")
        return True

    logger.info("Starting download (HTTP direct, resumable, progress)...")
    success = _try_download_via_http(model_name, str(cache_dir))

    if success:
        logger.info(GRADE)
        logger.info("  Embedding model READY: %s", model_name)
        logger.info("  Location: %s/hub/", cache_dir)
        logger.info(GRADE)
    else:
        logger.warning(WARNING_MSG)
    return success


def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    return 0 if ensure_model_downloaded(force=force) else 1


if __name__ == "__main__":
    raise SystemExit(main())
