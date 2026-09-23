# Neo4j Local Install (Docker-free) — Install/Configure/Start Guide

> Neo4j no longer depends on Docker. The distribution + bundled JRE install into the project environment
> `backend/.neo4j/` (sibling of `backend/.venv`), and the backend auto-starts it at launch
> (same pattern as MinerU); ragctl can directly control install/start/stop.

## Configuration-Driven (config.yml → `graph.*`, overridable by environment variables)

| Setting | Default | Description |
|---|---|---|
| `enabled` | true | Master switch for the knowledge graph |
| `mode` | `local` | `local` = local install, auto-started; `docker` = legacy docker compose |
| `auto_start` | true | Auto-start when the backend starts (lazy start, same as MinerU) |
| `bolt_port` / `http_port` | 7687 / 7474 | **Ports are customizable** (after changing, restarting the backend applies them automatically) |
| `username` / `password` | neo4j / `${NEO4J_PASSWORD:-123456}` | **Password is customizable**; initialized on first start via `neo4j-admin set-initial-password` (≥6 chars, same as the legacy docker setup) |
| `home` / `data_dir` / `log_dir` | `./backend/.neo4j` / `./neo4j_data` / `./neo4j_logs` | Install/data/log directories (relative to the project root) |
| `version` | 5.20.0 | Neo4j distribution version |
| `heap` / `pagecache` | 1G / 1G | Memory |
| `mirror` | empty = official | Download mirror (`dist.neo4j.org` / Adoptium API) |

## ragctl Control

```bash
ragctl start neo4j    # Install (first run auto-downloads + unzips + JRE + password init) + start; if installed, starts directly
ragctl stop neo4j     # Stop (kills the process tree by bolt port)
ragctl status         # Status includes the Neo4j :7687 line
ragctl up             # Start everything (the backend auto-starts Neo4j at launch)
```

## Install Behavior (performed automatically by `ragctl start neo4j`; can also be done manually)

1. Detect `backend/.neo4j/neo4j-community-*/bin` (if installed, skip the download)
2. Not installed → download the distribution (Windows: `-windows.zip`; Linux/macOS: `-unix.tar.gz`) +
   bundled JRE 17 (Temurin, per platform/architecture), unzip into `backend/.neo4j/`
3. Generate `conf/neo4j.conf` (ports/data dirs/memory/auth_minimum_password_length=6)
4. When the data directory is empty, run `neo4j-admin dbms set-initial-password <graph.password>`
5. Start the `neo4j console` subprocess; return after the bolt-port health check passes

## Cross-Platform Notes

- Windows: `neo4j.bat console` / `neo4j-admin.bat`; unzip the zip
- Linux/macOS: `bin/neo4j console` / `bin/neo4j-admin`; extract the tar.gz (chmod +x applied automatically)
- JRE: prefer system Java 17+ (`java -version`); otherwise use the bundled Temurin JRE
- Lifecycle: managed by the backend (Job Object/atexit; cleaned up when the backend exits);
  `ragctl start neo4j` runs in standalone mode (detach — keeps running after the CLI exits)

## FAQ

- **Password rejected (must be at least 8 characters)**: the default 123456 is already compatible via
  `auth_minimum_password_length=6`; custom passwords ≥8 chars avoid the issue entirely
- **Port already in use**: run `ragctl stop neo4j`, change `graph.bolt_port`/`http_port`, then restart
- **Change the password**: clear `neo4j_data/` (data will be rebuilt; rebuild the graph with kb_graph_build),
  then change `graph.password` and restart the backend
- **Offline environments**: pre-download the distribution + JRE into `backend/.neo4j/` (follow the zip/tar.gz
  naming convention; the manager detects the cache and skips the download)
