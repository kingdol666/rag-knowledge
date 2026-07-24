"""Config schema metadata — describes every configurable field for the UI."""
from __future__ import annotations
from typing import Any

CONFIG_SCHEMA: dict[str, Any] = {
    "server": {
        "label": "服务器配置",
        "icon": "CloudServerOutlined",
        "description": "前后端服务的端口、地址与跨域配置。修改端口需重启对应服务才能完全生效。",
        "fields": {
            "cors_origins": {
                "label": "CORS 允许来源", "type": "list",
                "description": '跨域允许的来源列表。["*"] 表示允许所有来源（开发推荐）。生产环境建议指定具体域名。',
                "default": ["*"],
            },
            "dev": {
                "label": "开发模式 (Dev)", "type": "group",
                "description": "APP_MODE=dev 时使用此段配置，启用热重载。",
                "fields": {
                    "host": {"label": "监听地址", "type": "string", "description": "后端绑定的网络接口。0.0.0.0 表示所有接口。", "default": "0.0.0.0"},
                    "backend_port": {"label": "后端端口", "type": "int", "description": "FastAPI 后端端口，默认 8765。", "default": 8765, "min": 1, "max": 65535},
                    "frontend_port": {"label": "前端端口", "type": "int", "description": "Nuxt 3 前端端口，默认 6789。", "default": 6789, "min": 1, "max": 65535},
                    "backend_url": {"label": "后端完整 URL", "type": "string", "description": "后端服务完整访问地址。", "default": "http://localhost:8765"},
                },
            },
            "prod": {
                "label": "生产模式 (Prod)", "type": "group",
                "description": "APP_MODE=prod 时使用此段配置，关闭热重载。",
                "fields": {
                    "host": {"label": "监听地址", "type": "string", "description": "后端绑定的网络接口。", "default": "0.0.0.0"},
                    "backend_port": {"label": "后端端口", "type": "int", "description": "生产环境后端端口，默认 8001。", "default": 8001, "min": 1, "max": 65535},
                    "frontend_port": {"label": "前端端口", "type": "int", "description": "生产环境前端端口，默认 3000。", "default": 3000, "min": 1, "max": 65535},
                    "backend_url": {"label": "后端完整 URL", "type": "string", "description": "生产环境后端完整访问地址。", "default": "http://localhost:8001"},
                },
            },
        },
    },
    "storage": {
        "label": "存储配置",
        "icon": "DatabaseOutlined",
        "description": "知识库文件系统的存储路径配置。",
        "fields": {
            "tree_fs_root": {
                "label": "知识库存储路径", "type": "string",
                "description": "tree-file-system 根目录路径（相对项目根或绝对路径）。环境变量 TREE_STORAGE_PATH 优先级更高。",
                "default": "./storage/tree-file-system",
            },
        },
    },
    "vector": {
        "label": "向量检索配置",
        "icon": "ThunderboltOutlined",
        "description": "ChromaDB 向量索引与检索参数，控制语义搜索行为。",
        "fields": {
            "enabled": {"label": "启用向量检索", "type": "boolean", "description": "开启后使用 ChromaDB 语义搜索。关闭则降级为纯 BM25 关键词搜索。", "default": True},
            "persist_dir": {"label": "ChromaDB 持久化目录", "type": "string", "description": "向量数据库持久化路径（相对项目根）。", "default": "./chroma_db"},
            "collection_prefix": {"label": "Collection 前缀", "type": "string", "description": "ChromaDB collection 名称前缀。", "default": "kb_"},
            "chunk_size": {"label": "文档分块大小", "type": "int", "description": "文档切分为向量块的最大字符数。", "default": 500, "min": 100, "max": 5000},
            "chunk_overlap": {"label": "分块重叠量", "type": "int", "description": "相邻文档块之间的重叠字符数。", "default": 50, "min": 0, "max": 500},
            "top_k": {"label": "返回结果数 (Top K)", "type": "int", "description": "向量搜索返回的最相似结果数。", "default": 5, "min": 1, "max": 50},
            "score_threshold": {"label": "文档相似度阈值", "type": "float", "description": "文档向量搜索最低余弦相似度。bge-m3 建议 0.3-0.5。", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01},
            "experience_score_threshold": {"label": "经验相似度阈值", "type": "float", "description": "经验库检索最低相似度，高于文档阈值。", "default": 0.55, "min": 0.0, "max": 1.0, "step": 0.01},
        },
    },
    "embedding": {
        "label": "Embedding 模型配置",
        "icon": "ExperimentOutlined",
        "description": "文本向量化模型参数，影响向量索引和搜索质量。",
        "fields": {
            "model_name": {"label": "模型名称", "type": "string", "description": "HuggingFace/ModelScope 模型标识符。默认 BAAI/bge-m3。", "default": "BAAI/bge-m3"},
            "cache_dir": {"label": "模型缓存目录", "type": "string", "description": "模型文件本地缓存路径。", "default": "./models_cache"},
            "device": {"label": "计算设备", "type": "select", "options": ["auto", "cuda", "cpu"], "description": "auto 自动检测 CUDA。", "default": "auto"},
            "batch_size": {"label": "批处理大小", "type": "int", "description": "单次推理的文档块数量。GPU 可增大加速。", "default": 32, "min": 1, "max": 256},
            "normalize": {"label": "向量归一化", "type": "boolean", "description": "L2 归一化后余弦相似度等于点积。", "default": True},
        },
    },
    "graph": {
        "label": "知识图谱配置 (Neo4j)",
        "icon": "ShareAltOutlined",
        "description": "Neo4j 图数据库连接与知识图谱构建参数。",
        "fields": {
            "enabled": {"label": "启用知识图谱", "type": "boolean", "description": "开启后使用 Neo4j 构建文档关系图谱。", "default": True},
            "uri": {"label": "Neo4j 连接 URI", "type": "string", "description": "Bolt 协议连接地址。", "default": "bolt://127.0.0.1:7687"},
            "username": {"label": "用户名", "type": "string", "description": "Neo4j 用户名。", "default": "neo4j"},
            "password": {"label": "密码", "type": "password", "description": "Neo4j 密码。环境变量 NEO4J_PASSWORD 优先级更高。", "default": ""},
            "database": {"label": "数据库名称", "type": "string", "description": "Neo4j 数据库名。", "default": "neo4j"},
            "pool": {
                "label": "连接池配置", "type": "group",
                "description": "Neo4j Driver 连接池参数。",
                "fields": {
                    "max_connection_pool_size": {"label": "最大连接数", "type": "int", "description": "连接池最大连接数。", "default": 50, "min": 1, "max": 500},
                    "connection_acquisition_timeout": {"label": "获取连接超时 (秒)", "type": "int", "description": "从连接池获取连接最大等待时间。", "default": 30, "min": 1, "max": 300},
                    "max_connection_lifetime": {"label": "连接最大生命周期 (秒)", "type": "int", "description": "连接最长存活时间。", "default": 3600, "min": 60, "max": 86400},
                },
            },
            "retry": {
                "label": "重试策略", "type": "group",
                "description": "瞬态失败的重试配置。",
                "fields": {
                    "max_attempts": {"label": "最大重试次数", "type": "int", "description": "操作失败后最大重试次数。", "default": 3, "min": 0, "max": 10},
                    "base_delay": {"label": "基础重试延迟 (秒)", "type": "float", "description": "首次重试等待时间，指数退避。", "default": 0.5, "min": 0.1, "max": 10.0, "step": 0.1},
                },
            },
        },
    },
    "search": {
        "label": "两阶段检索配置",
        "icon": "SearchOutlined",
        "description": "BM25 + 向量两阶段精准检索参数调优。",
        "fields": {
            "two_stage": {
                "label": "两阶段检索", "type": "group",
                "description": "Stage 1 BM25 广召回, Stage 2 向量精筛。",
                "fields": {
                    "enabled": {"label": "启用两阶段检索", "type": "boolean", "description": "开启后先 BM25 召回再向量精排。", "default": True},
                    "stage1_top_k": {"label": "Stage 1 召回数", "type": "int", "description": "BM25 候选文档数。", "default": 20, "min": 1, "max": 100},
                    "stage2_top_k": {"label": "Stage 2 精筛数", "type": "int", "description": "向量精筛后最终返回数。", "default": 5, "min": 1, "max": 50},
                    "stage1_keyword_weight": {"label": "关键词权重", "type": "float", "description": "BM25 关键词搜索权重。", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05},
                    "stage1_graph_weight": {"label": "图谱权重", "type": "float", "description": "知识图谱扩展权重。", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05},
                    "graph_neighbor_depth": {"label": "图谱邻居深度", "type": "int", "description": "图谱扩展搜索跳数。", "default": 1, "min": 1, "max": 5},
                    "min_candidates": {"label": "最少候选数", "type": "int", "description": "两阶段检索最低候选文档数。", "default": 3, "min": 1, "max": 20},
                },
            },
        },
    },
    "mineru": {
        "label": "MinerU OCR 引擎",
        "icon": "FileTextOutlined",
        "description": "PDF/DOCX 文档 OCR 解析引擎配置。端口自动分配。",
        "fields": {
            "enabled": {"label": "启用 MinerU", "type": "boolean", "description": "开启后自动拉起 MinerU OCR 引擎。", "default": True},
            "host": {"label": "MinerU 主机地址", "type": "string", "description": "MinerU API 绑定地址。", "default": "127.0.0.1"},
            "start_on_boot": {"label": "随后端启动", "type": "boolean", "description": "是否在后端启动时自动拉起。", "default": True},
            "startup_timeout": {"label": "启动超时 (秒)", "type": "int", "description": "等待 MinerU 就绪最大时间。", "default": 60, "min": 10, "max": 300},
            "model_source": {"label": "模型源", "type": "select", "options": ["modelscope", "huggingface"], "description": "modelscope 国内更快。", "default": "modelscope"},
        },
    },
    "experience_auto": {
        "label": "经验自动总结 (冥想记忆)",
        "icon": "BulbOutlined",
        "description": "定期自动从高频问题+知识库回答归纳经验草稿。类似 OpenClaw 冥想记忆：采集问题→匹配KB→验证文档→生成草稿。",
        "fields": {
            "enabled": {"label": "启用定时冥想", "type": "boolean", "description": "开启后按设定间隔自动运行经验归纳。草稿进入审核池，需确认后生效。", "default": False},
            "interval_hours": {"label": "运行间隔 (小时)", "type": "int", "description": "两次冥想循环之间的间隔。修改后下个周期热生效。", "default": 24, "min": 1, "max": 168},
            "lookback_days": {"label": "回溯天数", "type": "int", "description": "扫描最近N天的问答历史作为归纳源。", "default": 7, "min": 1, "max": 90},
            "min_cluster_count": {"label": "最小簇大小", "type": "int", "description": "同类问题至少出现N次才考虑归纳（过滤一次性问题）。", "default": 2, "min": 1, "max": 20},
            "max_drafts_per_run": {"label": "每轮最大草稿数", "type": "int", "description": "每轮冥想最多生成的经验草稿数（宁缺毋滥）。", "default": 5, "min": 1, "max": 50},
            "dry_run": {"label": "试运行模式", "type": "boolean", "description": "仅记录归纳结果到日志，不实际创建草稿。用于调优参数。", "default": False},
        },
    },
}
ENV_SCHEMA: dict[str, Any] = {
    "label": "环境变量 (.env)",
    "icon": "SettingOutlined",
    "description": "环境变量优先级高于 config.yml。修改后需重启对应服务完全生效。",
    "fields": {
        "APP_MODE": {"label": "运行模式", "type": "select", "options": ["dev", "prod"], "description": "dev = 开发模式（热重载）；prod = 生产模式。决定使用 config.yml 的 dev/prod 段落。", "default": "dev", "env_only": True},
        "BACKEND_PORT": {"label": "后端端口覆盖", "type": "int", "description": "覆盖 config.yml 后端端口。留空使用 config.yml 值。", "default": "", "env_only": True, "optional": True},
        "WEB_PORT": {"label": "前端端口覆盖", "type": "int", "description": "覆盖 config.yml 前端端口。留空使用 config.yml 值。", "default": "", "env_only": True, "optional": True},
        "TREE_STORAGE_PATH": {"label": "存储路径覆盖", "type": "string", "description": "覆盖 config.yml storage.tree_fs_root。留空使用 config.yml 值。", "default": "", "env_only": True, "optional": True},
        "NEO4J_PASSWORD": {"label": "Neo4j 密码", "type": "password", "description": "Neo4j 密码。优先级高于 config.yml graph.password。", "default": "", "env_only": True, "optional": True},
        "NO_RELOAD": {"label": "禁用热重载", "type": "select", "options": ["", "0", "1"], "description": "设为 1 即使 APP_MODE=dev 也不热重载。", "default": "", "env_only": True, "optional": True},
        "PYTHONUTF8": {"label": "强制 UTF-8", "type": "select", "options": ["", "0", "1"], "description": "设为 1 强制 Python UTF-8，解决 Windows GBK 问题。", "default": "", "env_only": True, "optional": True},
    },
}
