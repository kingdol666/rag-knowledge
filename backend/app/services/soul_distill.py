"""补天蒸馏服务 — LLM 蒸馏源材料为初始人格 + 一键创建 SOUL。

与 ragctl soul distill(dot-skill 产物目录)互补:
- ragctl soul distill: 输入 dot-skill 已产出的 persona.md/work.md/meta.json
- 本服务: 输入原始源材料(聊天记录/文档/描述) + 人格需求, 经 harness LLM
  按蒸馏 prompt 直接产出 persona/work/meta → 建库 + 4 文档 + bootstrap + 索引

前端"创建人格"表单提供蒸馏输入区, 走此端点; skill/ragctl 亦可调用。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.agent_harness_manager import agent_harness
from app.services.soul_config import resolve_soul_kb_path
from app.services.soul_training_db import log_event

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_TEMPLATE_DOCS = ["soul-definition.md", "values.md", "thinking-style.md", "memory-conventions.md"]


def _storage_root() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "storage" / "tree-file-system"


def _read_template(doc: str) -> str:
    p = _storage_root() / "soul-template" / doc
    return p.read_text(encoding="utf-8") if p.exists() else ""


async def distill_persona(personality_req: str, source_material: str,
                          name: str = "") -> dict[str, str]:
    """LLM 蒸馏: 源材料 + 需求 → {persona, work, meta}。

    使用 soul_distill_v1.txt prompt(身份/风格/思维/价值观/语言五维提取)。
    """
    prompt_path = _PROMPTS_DIR / "soul_distill_v1.txt"
    payload = json.dumps({
        "persona_name": name,
        "personality_req": personality_req[:2000],
        "source_material": source_material[:15000],
    }, ensure_ascii=False)
    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=2000,
    )
    text = (result.get("text") or "") if result.get("success") else ""
    parsed = _extract_json(text)
    if not parsed or not isinstance(parsed, dict):
        raise ValueError("蒸馏结果解析失败: " + (text[:200] if text else "LLM 无输出"))
    persona = str(parsed.get("persona", "")).strip()
    work = str(parsed.get("work", "")).strip()
    meta = parsed.get("meta") or {}
    if not persona and not work:
        raise ValueError("蒸馏结果为空(persona/work 均缺失)")
    return {
        "persona": persona,
        "work": work,
        "meta": json.dumps(meta, ensure_ascii=False),
    }


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    for marker in ("```json", "```"):
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            try:
                return json.loads(text[start:end].strip())
            except Exception:
                continue
    s, e = text.find("{"), text.rfind("}")
    if 0 <= s < e:
        try:
            return json.loads(text[s:e + 1])
        except Exception:
            return None
    return None


async def distill_and_create(name: str, kb_scope: list, domain_labels: list,
                             supported_task_types: list, harness: str,
                             personality_req: str, source_material: str,
                             progress_cb=None) -> dict:
    """蒸馏 + 建库 + 4 文档 + bootstrap + 索引(异步任务内调用)。"""
    from app.services import soul_training_db
    run_id = soul_training_db.start_run(name, "soul_distill", mode="distill")

    async def _cb(p):
        if progress_cb:
            r = progress_cb(p)
            if hasattr(r, "__await__"):
                await r
        soul_training_db.log_event(run_id, p.get("phase", "info"), p)

    try:
        await _cb({"phase": "distill", "msg": "LLM 蒸馏初始人格…"})
        distilled = await distill_persona(personality_req, source_material, name=name)
        meta = json.loads(distilled["meta"] or "{}")
        if not domain_labels:
            tags = meta.get("tags") or {}
            personality_tags = tags.get("personality") or []
            domain_labels = list(personality_tags)[:3]
            if meta.get("impression"):
                domain_labels.append(str(meta["impression"])[:12])
        if not supported_task_types:
            supported_task_types = ["知识答疑"]

        await _cb({"phase": "build", "msg": "创建知识库 + 4 人格文档…"})
        rep = await _create_from_docs(
            name, kb_scope, domain_labels, supported_task_types, harness,
            persona_text=distilled["persona"],
            work_text=distilled["work"],
            display_name=name,
        )
        await _cb({"phase": "done", "msg": "蒸馏完成", **rep})
        soul_training_db.finish_run(run_id, "done", rep)
        return rep
    except Exception as e:
        soul_training_db.finish_run(run_id, "error", {"error": str(e)})
        raise


async def create_from_template(name: str, kb_scope: list, domain_labels: list,
                               supported_task_types: list, harness: str) -> dict:
    """模板初始化(无蒸馏输入时的退化路径, 与 /api/soul/init 同语义)。"""
    return await _create_from_docs(
        name, kb_scope, domain_labels, supported_task_types, harness,
        persona_text="", work_text="", display_name=name)


async def _create_from_docs(name: str, kb_scope: list, domain_labels: list,
                            supported_task_types: list, harness: str,
                            persona_text: str, work_text: str,
                            display_name: str) -> dict:
    """建库 + 写 4 文档(模板+蒸馏融合) + bootstrap + 索引。"""
    # 建库 + 写 4 文档(模板+蒸馏融合) + bootstrap + 索引
    web_url = f"http://127.0.0.1:{_web_port()}"
    backend_url = _backend_url()

    # 1) 建库
    r = await _post_json(f"{web_url}/api/kb/create", {"name": name, "description": f"补天蒸馏人格: {display_name}"[:300]})
    if not r or not r.get("knowledgeBase"):
        raise RuntimeError(f"建库失败: {json.dumps(r, ensure_ascii=False)[:200]}")
    kb_id = r["knowledgeBase"]["id"]

    # 2) 4 文档(模板 + 蒸馏融合)
    tpl_def = _read_template("soul-definition.md")
    tpl_think = _read_template("thinking-style.md")
    tpl_values = _read_template("values.md")
    tpl_mem = _read_template("memory-conventions.md")
    if persona_text:
        soul_def = f"{tpl_def}\n\n---\n\n# 补天蒸馏人格: {display_name}\n\n{persona_text}\n"
    else:
        soul_def = tpl_def
    if work_text:
        think = f"{tpl_think}\n\n---\n\n# 补天蒸馏工作方式: {display_name}\n\n{work_text}\n"
    else:
        think = tpl_think
    for doc, content in (("soul-definition.md", soul_def), ("thinking-style.md", think),
                         ("values.md", tpl_values), ("memory-conventions.md", tpl_mem)):
        await _post_json(f"{web_url}/api/kb/documents/create",
                         {"kbId": kb_id, "name": doc, "content": content})

    # 3) bootstrap
    boot = await _post_json(f"{backend_url}/api/v1/soul/bootstrap", {
        "soul_kb_id": kb_id,
        "kb_scope": kb_scope if kb_scope else ["*"],
        "domain_labels": domain_labels or [],
        "supported_task_types": supported_task_types or [],
        "harness": harness or "",
        "model": "",
    })

    # 4) 索引 4 文档
    for doc in _TEMPLATE_DOCS:
        try:
            await _post_json(f"{backend_url}/api/v1/search/index-document",
                             {"kb_id": kb_id, "doc_path": doc})
        except Exception:
            pass

    return {
        "success": True,
        "kb_id": kb_id,
        "name": name,
        "mode": "distill" if persona_text else "template",
        "docs_created": len(_TEMPLATE_DOCS),
        "profile_summary_generated": bool(boot.get("profile_summary_generated")),
        "meditation_config_created": bool(boot.get("meditation_config_created")),
    }


async def _post_json(url: str, body: dict) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {url} → HTTP {r.status_code}: {r.text[:200]}")
        return r.json()


def _web_port() -> int:
    try:
        from app.config import config as _c
        return int(_c.frontend_port or 6789)
    except Exception:
        return 6789


def _backend_url() -> str:
    try:
        from app.config import config as _c
        return f"http://localhost:{_c.api_port}"
    except Exception:
        return "http://localhost:8765"
