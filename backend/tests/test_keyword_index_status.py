# -*- coding: utf-8 -*-
"""keyword_index_status 就绪面单测（2026-11-13 修复轮）。

背景 1：_build_keyword_index 以 ``self._keyword_built = True`` 发布（实例属性），
健康面必须读实例状态而非类属性——classmethod 版本曾永远返回 ready=False（实测）。
背景 2：_keyword_lock 会被整个 BM25 构建长时间持有；健康面必须无锁读取，
否则 async 健康端点在构建期间冻结事件循环且 building:true 不可观测（评审实证）。
"""
import threading

from app.services.two_stage_search_service import TwoStageSearchService, _keyword_lock


def test_status_reflects_instance_state_without_lock_held():
    svc = TwoStageSearchService()
    with _keyword_lock:
        svc._keyword_built = True      # 实例属性（与 _build_keyword_index 的发布方式一致）
        svc._keyword_building = False
        status = svc.keyword_index_status()
    assert status == {"ready": True, "building": False}


def test_status_reflects_building_state():
    svc = TwoStageSearchService()
    with _keyword_lock:
        svc._keyword_built = False
        svc._keyword_building = True
        status = svc.keyword_index_status()
    assert status == {"ready": False, "building": True}


def test_status_default_is_not_ready():
    # 独立实例无实例属性时，落到类默认（False/False）——不依赖其他测试的清理。
    svc = TwoStageSearchService()
    assert svc.keyword_index_status() == {"ready": False, "building": False}


def test_status_read_never_blocks_on_builder_lock():
    """模拟构建者长时间持锁：status 读取必须立即返回（无锁语义）。"""
    svc = TwoStageSearchService()
    with _keyword_lock:                      # 主线程持锁期间（等价于构建中）
        svc._keyword_built = False
        svc._keyword_building = True         # 构建标志在锁内写入
        result: list = []

        def probe():
            result.append(svc.keyword_index_status())

        t = threading.Thread(target=probe, daemon=True)
        t.start()
        t.join(timeout=2.0)
    assert not t.is_alive(), "status read blocked on the builder lock"
    assert result == [{"ready": False, "building": True}]
