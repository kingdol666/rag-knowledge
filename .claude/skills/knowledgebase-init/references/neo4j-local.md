# Neo4j 本地安装（Docker-free）— 安装/配置/启动指南

> Neo4j 不再依赖 Docker。发行版 + 内置 JRE 安装在项目环境
> `backend/.neo4j/`（与 `backend/.venv` 同级），backend 启动时自动拉起
> （与 MinerU 同模式），ragctl 可直接控制 安装/启动/停止。

## 配置驱动（config.yml → `graph.*`，环境变量可覆盖）

| 配置项 | 默认 | 说明 |
|---|---|---|
| `enabled` | true | 图谱总开关 |
| `mode` | `local` | `local`=本地安装自动启动；`docker`=旧 docker compose |
| `auto_start` | true | backend 启动时自动拉起（懒启动，同 MinerU） |
| `bolt_port` / `http_port` | 7687 / 7474 | **端口自定义**（改后重启 backend 自动生效） |
| `username` / `password` | neo4j / `${NEO4J_PASSWORD:-123456}` | **密码自定义**；首启经 `neo4j-admin set-initial-password` 初始化（≥6 位，与旧 docker 一致） |
| `home` / `data_dir` / `log_dir` | `./backend/.neo4j` / `./neo4j_data` / `./neo4j_logs` | 安装/数据/日志目录（项目根相对） |
| `version` | 5.20.0 | Neo4j 发行版版本 |
| `heap` / `pagecache` | 1G / 1G | 内存 |
| `mirror` | 空=官方 | 下载镜像（`dist.neo4j.org` / Adoptium API） |

## ragctl 控制

```bash
ragctl start neo4j    # 安装(首次自动下载+解压+JRE+密码初始化)+启动；已装则直接启动
ragctl stop neo4j     # 停止（按 bolt 端口杀进程树）
ragctl status         # 状态含 Neo4j :7687 行
ragctl up             # 启动全部（backend 启动时自动拉起 Neo4j）
```

## 安装行为（ragctl start neo4j 自动完成，也可手动）

1. 检测 `backend/.neo4j/neo4j-community-*/bin`（已装则跳过下载）
2. 未装 → 下载发行版（Windows: `-windows.zip`；Linux/macOS: `-unix.tar.gz`）+
   内置 JRE 17（Temurin，按平台/架构），解压到 `backend/.neo4j/`
3. 生成 `conf/neo4j.conf`（端口/数据目录/内存/auth_minimum_password_length=6）
4. 数据目录为空时执行 `neo4j-admin dbms set-initial-password <graph.password>`
5. `neo4j console` 子进程启动，健康检查 bolt 端口后返回

## 跨平台说明

- Windows: `neo4j.bat console` / `neo4j-admin.bat`；zip 解压
- Linux/macOS: `bin/neo4j console` / `bin/neo4j-admin`；tar.gz 解压（自动 chmod +x）
- JRE: 优先系统 Java 17+（`java -version`），否则用内置 Temurin JRE
- 生命周期: backend 托管（Job Object/atexit，随 backend 退出清理）；
  `ragctl start neo4j` 独立模式（detach，CLI 退出后持续运行）

## 常见问题

- **密码被拒（must be at least 8 characters）**：默认 123456 已通过
  `auth_minimum_password_length=6` 兼容；自定义密码 ≥8 位无此问题
- **端口被占用**：`ragctl stop neo4j` 后改 `graph.bolt_port`/`http_port` 重启
- **换密码**：清空 `neo4j_data/`（数据会重建，图谱用 kb_graph_build 重建）后
  改 `graph.password` 重启 backend
- **离线环境**：预下载发行版+JRE 放入 `backend/.neo4j/`（zip/tar.gz 文件名规范，
  manager 检测到缓存跳过下载）
