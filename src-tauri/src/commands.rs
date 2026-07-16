// RAG Knowledge Desktop — Tauri 命令实现
//
// 所有命令都基于"项目根目录"（project_root）定位 backend/web/config。
// dev 模式 project_root = src-tauri 的父目录；打包后读 RAG_PROJECT_ROOT 环境变量。

use serde::Serialize;
use std::collections::HashMap;
use std::io::{Read, Seek, SeekFrom};
use std::net::TcpStream;
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::State;

const BACKEND_PORT_DEFAULT: u16 = 8765;
const WEB_PORT_DEFAULT: u16 = 6789;

// ── 共享状态：记录本会话启动的 PID（用于 stop） ──
#[derive(Default)]
pub struct AppState {
    pub pids: Mutex<HashMap<String, u32>>,
}

// ── 返回类型 ──
#[derive(Serialize, Clone)]
pub struct ServiceResult {
    pub success: bool,
    pub message: String,
    pub pid: Option<u32>,
}

#[derive(Serialize, Clone)]
pub struct StatusSnapshot {
    pub backend: bool,
    pub web: bool,
    pub neo4j: bool,
    pub mineru: bool,
    pub backend_health: Option<String>,
    pub mineru_port: Option<u16>,
    pub backend_url: String,
    pub web_url: String,
}

#[derive(Serialize, Clone)]
pub struct Features {
    pub vector_enabled: bool,
    pub graph_enabled: bool,
    pub mineru_enabled: bool,
    pub auth_enabled: bool,
    pub backend_url: String,
    pub web_url: String,
    pub neo4j_uri: String,
    pub storage_path: String,
    pub project_root: String,
    pub app_mode: String,
    pub backend_port: u16,
    pub web_port: u16,
}

#[derive(Serialize, Clone)]
pub struct Ports {
    pub backend: u16,
    pub web: u16,
}

#[derive(Serialize, Clone)]
pub struct Environment {
    pub mode: String,           // "dev" or "prod"
    pub backend_port: u16,
    pub web_port: u16,
    pub backend_url: String,
    pub web_url: String,
}

#[derive(Serialize, Clone)]
pub struct LogLine {
    pub service: String,
    pub line: String,
}

#[derive(Serialize, Clone)]
pub struct CmdOutput {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: Option<i32>,
}

// ── 路径 / 配置辅助 ──

pub fn project_root_str() -> String {
    if let Ok(root) = std::env::var("RAG_PROJECT_ROOT") {
        return root.replace('\\', "/");
    }
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    Path::new(manifest_dir)
        .parent()
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .unwrap_or_else(|| ".".to_string())
}

fn read_config_yml() -> serde_yaml::Value {
    let path = format!("{}/config.yml", project_root_str());
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    serde_yaml::from_str(&content).unwrap_or(serde_yaml::Value::Null)
}

fn read_backend_config_yml() -> serde_yaml::Value {
    let path = format!("{}/backend/config.yml", project_root_str());
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    serde_yaml::from_str(&content).unwrap_or(serde_yaml::Value::Null)
}

// ── .env 文件读写 ───────────────────────────────────────────────────────────

/// 从项目根目录的 .env 文件中读取键值对
fn read_dotenv() -> HashMap<String, String> {
    let path = format!("{}/.env", project_root_str());
    let mut map = HashMap::new();
    if let Ok(content) = std::fs::read_to_string(&path) {
        for line in content.lines() {
            let l = line.trim();
            if l.is_empty() || l.starts_with('#') {
                continue;
            }
            if let Some(idx) = l.find('=') {
                let k = l[..idx].trim().to_string();
                let v = l[idx + 1..].trim().to_string();
                map.insert(k, v);
            }
        }
    }
    map
}

/// 读取当前 APP_MODE（优先级: 进程环境变量 > .env 文件 > 默认 "dev"）
pub fn read_app_mode() -> String {
    // 1. 进程环境变量（子进程继承）
    if let Ok(mode) = std::env::var("APP_MODE") {
        let m = mode.trim().to_lowercase();
        if m == "prod" || m == "production" {
            return "prod".to_string();
        }
        if m == "dev" || m == "development" {
            return "dev".to_string();
        }
        // 未知值保留原值，但默认走 prod 分支:
        return mode;
    }
    // 2. .env 文件
    let dotenv = read_dotenv();
    if let Some(mode) = dotenv.get("APP_MODE") {
        let m = mode.trim().to_lowercase();
        if m == "prod" || m == "production" {
            return "prod".to_string();
        }
        if m == "dev" || m == "development" {
            return "dev".to_string();
        }
    }
    // 3. 默认
    "dev".to_string()
}

/// 从 config.yml 根据 mode 读取端口，返回值同时被 .env 的 BACKEND_PORT / WEB_PORT 覆盖
fn resolve_ports_from_config(mode: &str) -> (u16, u16) {
    let cfg = read_config_yml();
    let section = &cfg["server"][mode];
    let env_backend = std::env::var("BACKEND_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .or_else(|| read_dotenv().get("BACKEND_PORT").and_then(|v| v.parse().ok()));
    let env_web = std::env::var("WEB_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .or_else(|| read_dotenv().get("WEB_PORT").and_then(|v| v.parse().ok()));
    let backend = env_backend.unwrap_or(
        section["backend_port"].as_u64().unwrap_or(BACKEND_PORT_DEFAULT as u64) as u16,
    );
    let web = env_web.unwrap_or(
        section["frontend_port"].as_u64().unwrap_or(WEB_PORT_DEFAULT as u64) as u16,
    );
    (backend, web)
}

pub fn get_ports() -> Ports {
    let mode = read_app_mode();
    let (backend, web) = resolve_ports_from_config(&mode);
    Ports { backend, web }
}

// ── 命令：项目根 / 端口 / 功能探测 ──

#[tauri::command]
pub fn project_root() -> String {
    project_root_str()
}

#[tauri::command]
pub fn read_ports() -> Ports {
    get_ports()
}

// ── 环境切换命令 ────────────────────────────────────────────────────────────

#[tauri::command]
pub fn get_environment() -> Environment {
    let mode = read_app_mode();
    let (backend_port, web_port) = resolve_ports_from_config(&mode);
    Environment {
        mode,
        backend_port,
        web_port,
        backend_url: format!("http://localhost:{}", backend_port),
        web_url: format!("http://localhost:{}", web_port),
    }
}

/// 切换运行环境（dev / prod）
///
/// 将 APP_MODE 写入项目根 .env 文件，并同步更新 BACKEND_PORT / WEB_PORT
/// 以匹配对应环境在 config.yml 中的默认端口。
/// 如果前端传 stop_running=true，先尝试停止当前模式下的所有服务，
/// 避免端口冲突。
#[tauri::command]
pub async fn set_environment(
    mode: String,
    app: tauri::AppHandle,
) -> Result<Environment, String> {
    let m = match mode.trim().to_lowercase().as_str() {
        "prod" | "production" => "prod",
        "dev" | "development" => "dev",
        other => return Err(format!(
            "无效环境: {} — 可选: dev / prod",
            other
        )),
    };

    let current = read_app_mode();
    if current == m {
        // 模式未变，直接返回当前配置
        return Ok(get_environment());
    }

    let (backend_port, web_port) = resolve_ports_from_config(m);
    let root = project_root_str();

    // ── 1. 停止当前模式下的服务 ──
    emit_progress(&app, "env", "info", &format!(
        "切换环境 {} → {}（停止现有服务…）",
        current, m,
    ));

    // 先关闭 web（不阻塞），再关闭 backend（确保 MinerU 随 backend lifespan 杀干净）
    for svc in &["web", "backend"] {
        let port = if *svc == "web" {
            get_ports().web
        } else {
            get_ports().backend
        };
        if let Some(pid) = find_pid_on_port(port) {
            let _ = emit_progress(
                &app, "env", "info",
                &format!("停止 {} (pid={}, port={})", svc, pid, port),
            );
            kill_pid(pid);
            // 等端口释放
            for _ in 0..15 {
                std::thread::sleep(Duration::from_millis(400));
                if find_pid_on_port(port).is_none() {
                    break;
                }
            }
        }
    }

    // ── 2. 写 .env ──
    let env_path = format!("{}/.env", root);
    let mut dotenv = read_dotenv();
    dotenv.insert("APP_MODE".to_string(), m.to_string());
    dotenv.insert("BACKEND_PORT".to_string(), backend_port.to_string());
    dotenv.insert("WEB_PORT".to_string(), web_port.to_string());

    let _ = std::fs::copy(&env_path, format!("{}.bak", env_path));
    let mut lines = vec![
        "# ============================================".to_string(),
        "# RAG Knowledge Platform - Environment Variables".to_string(),
        "# ============================================".to_string(),
        "# Env vars override config.yml values.".to_string(),
        "# Managed via Tauri desktop console.".to_string(),
        "# ============================================".to_string(),
        "".to_string(),
    ];
    let known = [
        "APP_MODE", "BACKEND_PORT", "WEB_PORT",
        "BACKEND_URL", "TREE_STORAGE_PATH",
        "HF_ENDPOINT", "NEO4J_PASSWORD", "KB_AUTH_TOKEN", "PYTHONUTF8",
    ];
    for k in known {
        if let Some(v) = dotenv.get(k) {
            if v.is_empty() {
                lines.push(format!("# {}=", k));
            } else {
                lines.push(format!("{}={}", k, v));
            }
        }
    }
    for (k, v) in &dotenv {
        if known.contains(&k.as_str()) {
            continue;
        }
        if v.is_empty() {
            lines.push(format!("# {}=", k));
        } else {
            lines.push(format!("{}={}", k, v));
        }
    }
    lines.push("".to_string());
    std::fs::write(&env_path, lines.join("\n"))
        .map_err(|e| format!("写 .env 失败: {}", e))?;

    emit_progress(&app, "env", "done", &format!(
        "✓ 环境已切换至 {} — backend :{} / web :{}",
        m, backend_port, web_port,
    ));

    Ok(Environment {
        mode: m.to_string(),
        backend_port,
        web_port,
        backend_url: format!("http://localhost:{}", backend_port),
        web_url: format!("http://localhost:{}", web_port),
    })
}

#[tauri::command]
pub fn detect_features() -> Result<Features, String> {
    let cfg = read_config_yml();
    let backend_cfg = read_backend_config_yml();
    let ports = get_ports();
    let mode = read_app_mode();
    Ok(Features {
        vector_enabled: cfg["vector"]["enabled"].as_bool().unwrap_or(false),
        graph_enabled: cfg["graph"]["enabled"].as_bool().unwrap_or(false),
        mineru_enabled: backend_cfg["mineru"]["enabled"].as_bool().unwrap_or(false),
        auth_enabled: cfg["server"]["auth"]["enabled"].as_bool().unwrap_or(false),
        backend_url: format!("http://localhost:{}", ports.backend),
        web_url: format!("http://localhost:{}", ports.web),
        neo4j_uri: cfg["graph"]["uri"].as_str().unwrap_or("").to_string(),
        storage_path: cfg["storage"]["tree_fs_root"].as_str().unwrap_or("").to_string(),
        project_root: project_root_str(),
        app_mode: mode,
        backend_port: ports.backend,
        web_port: ports.web,
    })
}

// ── TCP 端口检测（同步，预检用） ──
fn port_is_listening(port: u16) -> bool {
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_millis(500),
    )
    .is_ok()
}

// ── 命令：服务启动 / 停止 ──

#[tauri::command]
pub async fn start_service(
    service: String,
    state: State<'_, AppState>,
) -> Result<ServiceResult, String> {
    let root = project_root_str();
    let ports = get_ports();
    let mode = read_app_mode();

    // ── 预检：目标端口是否已被占用 ──
    let pre_check = |name: &str, port: u16| -> Result<(), String> {
        if port_is_listening(port) {
            let pid = find_pid_on_port(port);
            Err(format!(
                "{} 已在运行（port {} 被占用{}）— 请先停止再启动",
                name,
                port,
                pid.map(|p| format!(", pid={}", p)).unwrap_or_default(),
            ))
        } else {
            Ok(())
        }
    };

    let res = match service.as_str() {
        "backend" => {
            pre_check("Backend", ports.backend)?;
            spawn_backend(&root, &mode)?
        }
        "web" => {
            pre_check("Web", ports.web)?;
            spawn_web(&root, &mode)?
        }
        "neo4j" => return start_neo4j(&root).await,
        "all" => {
            pre_check("Backend", ports.backend)?;
            let mut b = spawn_backend(&root, &mode)?;
            if port_is_listening(ports.web) {
                let pid = find_pid_on_port(ports.web);
                b.message.push_str(&format!(
                    "\n Web 已在运行 (port {} {}), 跳过",
                    ports.web,
                    pid.map(|p| format!("pid={}", p)).unwrap_or_default(),
                ));
            } else {
                match spawn_web(&root, &mode) {
                    Ok(w) => {
                        if let Some(pid) = w.pid {
                            state.pids.lock().unwrap().insert("web".into(), pid);
                            b.message.push_str(&format!("\n web pid={}", pid));
                        }
                    }
                    Err(e) => b.message.push_str(&format!("\n web 启动失败: {}", e)),
                }
            }
            b
        }
        other => return Err(format!("未知服务: {}（可选: backend / web / neo4j / all）", other)),
    };
    if let Some(pid) = res.pid {
        state.pids.lock().unwrap().insert(service.clone(), pid);
    }
    Ok(res)
}

fn spawn_backend(root: &str, mode: &str) -> Result<ServiceResult, String> {
    let dir = format!("{}/backend", root);
    let log_dir = format!("{}/logs", dir);
    let _ = std::fs::create_dir_all(&log_dir);
    let stdout_path = format!("{}/desktop-stdout.log", log_dir);
    let out = std::fs::OpenOptions::new()
        .create(true).write(true).truncate(true)
        .open(&stdout_path)
        .map_err(|e| format!("无法写日志 {}: {}", stdout_path, e))?;
    let err = out.try_clone().map_err(|e| e.to_string())?;

    let uv = find_uv()
        .ok_or_else(|| "uv 未找到 — 请先点「一键引导」安装 uv，或重启 Tauri 让新 PATH 生效".to_string())?;
    let ports = get_ports();
    let child = Command::new(&uv)
        .args(["run", "python", "main.py"])
        .current_dir(&dir)
        .env("APP_MODE", mode)
        .env("BACKEND_PORT", ports.backend.to_string())
        .env("PYTHONUTF8", "1")
        .env("PATH", enriched_path())
        .stdout(Stdio::from(out))
        .stderr(Stdio::from(err))
        .spawn()
        .map_err(|e| format!("启动 uv 失败: {}（uv={}）", e, uv))?;

    let pid = child.id();
    std::mem::forget(child); // detach：进程随桌面 app 独立运行，不被 Drop 影响
    Ok(ServiceResult {
        success: true,
        message: format!(
            "Backend 启动中（mode={}，uv run python main.py，cwd={}，pid={}，port={}，log={}）",
            mode, dir, pid, ports.backend, stdout_path
        ),
        pid: Some(pid),
    })
}

fn spawn_web(root: &str, mode: &str) -> Result<ServiceResult, String> {
    let dir = format!("{}/web", root);
    let log_dir = format!("{}/logs", dir);
    let _ = std::fs::create_dir_all(&log_dir);
    let stdout_path = format!("{}/desktop-stdout.log", log_dir);
    let out = std::fs::OpenOptions::new()
        .create(true).write(true).truncate(true)
        .open(&stdout_path)
        .map_err(|e| e.to_string())?;
    let err = out.try_clone().map_err(|e| e.to_string())?;

    let ports = get_ports();
    let child = Command::new("node")
        .args(["start.mjs"])
        .current_dir(&dir)
        .env("APP_MODE", mode)
        .env("WEB_PORT", ports.web.to_string())
        .env("PATH", enriched_path())
        .stdout(Stdio::from(out))
        .stderr(Stdio::from(err))
        .spawn()
        .map_err(|e| format!("启动 node 失败: {}（确认 node 已装）", e))?;

    let pid = child.id();
    std::mem::forget(child);
    Ok(ServiceResult {
        success: true,
        message: format!(
            "Web 启动中（mode={}，node start.mjs，cwd={}，pid={}，port={}）",
            mode, dir, pid, ports.web
        ),
        pid: Some(pid),
    })
}

async fn start_neo4j(root: &str) -> Result<ServiceResult, String> {
    let output = tokio::process::Command::new("docker")
        .args(["compose", "up", "-d", "neo4j"])
        .current_dir(root)
        .output()
        .await
        .map_err(|e| format!("docker 启动失败: {}（确认 Docker Desktop 运行中）", e))?;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    if output.status.success() {
        Ok(ServiceResult {
            success: true,
            message: format!("Neo4j 容器已启动\n{}", stdout.trim()),
            pid: None,
        })
    } else {
        Err(format!("docker compose 失败:\n{}", stderr.trim()))
    }
}

#[tauri::command]
pub async fn stop_service(
    service: String,
    state: State<'_, AppState>,
) -> Result<ServiceResult, String> {
    let ports = get_ports();
    // 优先用记录的 PID，回退到端口查 PID（应对 app 外启动的服务）
    let recorded = state.pids.lock().unwrap().get(&service).copied();
    let port_pid = match service.as_str() {
        "backend" => find_pid_on_port(ports.backend),
        "web" => find_pid_on_port(ports.web),
        _ => None,
    };
    // 端口占用者优先（当前真正在跑的进程）；fallback 到启动器记录的 PID
    let target = port_pid.or(recorded);

    let pid = match target {
        Some(p) => p,
        None => {
            return Ok(ServiceResult {
                success: false,
                message: format!("{} 未在运行（无 PID 记录且端口空闲）", service),
                pid: None,
            })
        }
    };

    let killed = kill_pid(pid);
    state.pids.lock().unwrap().remove(&service);
    if killed {
        Ok(ServiceResult {
            success: true,
            message: format!("{} 已停止 (pid={})", service, pid),
            pid: Some(pid),
        })
    } else {
        Err(format!("无法停止 pid={}（可能已退出或权限不足）", pid))
    }
}

fn find_pid_on_port(port: u16) -> Option<u32> {
    #[cfg(windows)]
    {
        let out = Command::new("cmd")
            .args(["/c", &format!("netstat -ano | findstr :{} | findstr LISTENING", port)])
            .output()
            .ok()?;
        let s = String::from_utf8_lossy(&out.stdout);
        s.lines()
            .next()
            .and_then(|l| l.split_whitespace().last())
            .and_then(|x| x.parse().ok())
    }
    #[cfg(not(windows))]
    {
        let out = Command::new("sh")
            .args([
                "-c",
                &format!("lsof -ti:{} 2>/dev/null || ss -tlnp 2>/dev/null | grep ':{}'", port, port),
            ])
            .output()
            .ok()?;
        String::from_utf8_lossy(&out.stdout)
            .trim()
            .lines()
            .next()
            .and_then(|l| l.trim().parse().ok())
    }
}

fn kill_pid(pid: u32) -> bool {
    #[cfg(windows)]
    {
        Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/F", "/T"])
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }
    #[cfg(not(windows))]
    {
        Command::new("kill")
            .args(["-9", &pid.to_string()])
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }
}

// ── 命令：状态检测（HTTP + TCP） ──

/// 一键停止所有正在运行的服务（backend + web + 所有已知端口上的孤儿进程）。
/// 顺序：先 web 后 backend，确保 backend 的 lifespan 先 kill MinerU。
/// 然后在所有已知端口范围内（dev/prod 两个模式的端口）扫描并清理残留 PID。
#[tauri::command]
pub async fn stop_all_services(
    state: State<'_, AppState>,
    app: tauri::AppHandle,
) -> Result<ServiceResult, String> {
    let ports = get_ports();
    let dev_ports = resolve_ports_from_config("dev");
    let prod_ports = resolve_ports_from_config("prod");

    // 所有可能的端口（防止模式切换后旧端口残留）
    let all_backend_ports = [dev_ports.0, prod_ports.0, ports.backend];
    let all_web_ports = [dev_ports.1, prod_ports.1, ports.web];

    let mut stopped = Vec::new();
    let mut failed = Vec::new();

    emit_progress(&app, "stop_all", "info", "■ 一键停止所有服务…");

    // 1. 先停 web（不阻塞 backend 的 lifespan 关闭）
    for &port in &all_web_ports {
        if let Some(pid) = find_pid_on_port(port) {
            emit_progress(&app, "stop_all", "info", &format!("停止 Web (pid={}, port={})", pid, port));
            if kill_pid(pid) {
                stopped.push(format!("Web(pid={},port={})", pid, port));
                // 等端口释放
                wait_port_free(port, 8);
            } else {
                failed.push(format!("Web(pid={})", pid));
            }
        }
    }

    // 2. 停 backend（会触发 lifespan → stop MinerU via Job Object）
    for &port in &all_backend_ports {
        if let Some(pid) = find_pid_on_port(port) {
            emit_progress(&app, "stop_all", "info", &format!("停止 Backend (pid={}, port={})", pid, port));
            if kill_pid(pid) {
                stopped.push(format!("Backend(pid={},port={})", pid, port));
                // 给 backend lifespan 时间清理 MinerU + 释放端口
                wait_port_free(port, 12);
            } else {
                failed.push(format!("Backend(pid={})", pid));
            }
        }
    }

    // 3. 兜底扫描：清理所有已知端口上残留的孤儿进程
    for (label, port) in [
        ("Backend", ports.backend),
        ("Web", ports.web),
    ] {
        if let Some(pid) = find_pid_on_port(port) {
            emit_progress(&app, "stop_all", "warn", &format!(
                "清理残留 {} 进程 (pid={}, port={})", label, pid, port
            ));
            if kill_pid(pid) {
                stopped.push(format!("残留{}(pid={})", label, pid));
                wait_port_free(port, 5);
            }
        }
    }

    // 清空记录
    state.pids.lock().unwrap().clear();

    if failed.is_empty() {
        let msg = if stopped.is_empty() {
            "所有端口空闲 — 无运行中的服务".to_string()
        } else {
            format!("已停止: {}", stopped.join(", "))
        };
        emit_progress(&app, "stop_all", "done", &msg);
        Ok(ServiceResult { success: true, message: msg, pid: None })
    } else {
        let msg = format!("部分停止: {} / 失败: {}", stopped.join(", "), failed.join(", "));
        emit_progress(&app, "stop_all", "error", &msg);
        Err(msg)
    }
}

/// 等待端口空闲（最多 wait_secs 秒）
fn wait_port_free(port: u16, wait_secs: u32) {
    for _ in 0..(wait_secs * 5) {
        if !port_is_listening(port) {
            return;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
}

// ── 命令：状态检测（HTTP + TCP） ──

#[tauri::command]
pub async fn check_status() -> Result<StatusSnapshot, String> {
    let ports = get_ports();
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;
    let backend_url = format!("http://localhost:{}", ports.backend);
    let web_url = format!("http://localhost:{}", ports.web);

    let mut snap = StatusSnapshot {
        backend: false,
        web: false,
        neo4j: false,
        mineru: false,
        backend_health: None,
        mineru_port: None,
        backend_url: backend_url.clone(),
        web_url: web_url.clone(),
    };

    // backend health
    if let Ok(r) = client
        .get(format!("{}/api/v1/health", backend_url))
        .send()
        .await
    {
        if r.status().is_success() {
            snap.backend = true;
            if let Ok(json) = r.json::<serde_json::Value>().await {
                snap.backend_health = json
                    .get("status")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());
            }
        }
    }

    // web
    if let Ok(r) = client
        .get(format!("{}/api/config/frontend", web_url))
        .send()
        .await
    {
        if r.status().is_success() {
            snap.web = true;
        }
    }

    // neo4j (TCP probe 7687)
    snap.neo4j = tokio::net::TcpStream::connect("127.0.0.1:7687").await.is_ok();

    // mineru (via backend)
    if snap.backend {
        if let Ok(r) = client
            .get(format!("{}/api/v1/mineru/status", backend_url))
            .send()
            .await
        {
            if let Ok(json) = r.json::<serde_json::Value>().await {
                snap.mineru = json
                    .get("running")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                snap.mineru_port = json
                    .get("port")
                    .and_then(|v| v.as_u64())
                    .map(|p| p as u16);
            }
        }
    }

    Ok(snap)
}

// ── 命令：修复 ──

#[tauri::command]
pub async fn repair_service(target: String) -> Result<ServiceResult, String> {
    let root = project_root_str();
    match target.as_str() {
        "neo4j" => start_neo4j(&root).await,
        "backend_deps" => run_cmd_async("uv", &["sync"], &format!("{}/backend", root)).await,
        "web_deps" => run_cmd_async("npm", &["install"], &format!("{}/web", root)).await,
        other => Err(format!(
            "未知修复目标: {}（可选: neo4j / backend_deps / web_deps）",
            other
        )),
    }
}

async fn run_cmd_async(prog: &str, args: &[&str], cwd: &str) -> Result<ServiceResult, String> {
    let out = tokio::process::Command::new(prog)
        .args(args)
        .current_dir(cwd)
        .output()
        .await
        .map_err(|e| format!("运行 {} 失败: {}", prog, e))?;
    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let stderr = String::from_utf8_lossy(&out.stderr).to_string();
    if out.status.success() {
        Ok(ServiceResult {
            success: true,
            message: format!("{} {} 完成\n{}", prog, args.join(" "), stdout.trim()),
            pid: None,
        })
    } else {
        Err(format!("{} {} 失败:\n{}", prog, args.join(" "), stderr.trim()))
    }
}

// ── 命令：日志 / Web UI / ragctl ──

#[tauri::command]
pub fn read_log_tail(service: String, lines: Option<usize>) -> Result<String, String> {
    let root = project_root_str();
    let path = match service.as_str() {
        "backend" => format!("{}/backend/logs/desktop-stdout.log", root),
        "mineru" => format!("{}/backend/logs/mineru-api.log", root),
        "web" => format!("{}/web/logs/desktop-stdout.log", root),
        other => return Err(format!("未知日志: {}（可选: backend / web / mineru）", other)),
    };
    let content =
        std::fs::read_to_string(&path).map_err(|e| format!("读取 {} 失败: {}", path, e))?;
    let n = lines.unwrap_or(200);
    let all: Vec<&str> = content.lines().collect();
    let start = all.len().saturating_sub(n);
    Ok(all[start..].join("\n"))
}

fn get_log_path(service: &str, root: &str) -> Result<String, String> {
    match service {
        "backend" => Ok(format!("{}/backend/logs/desktop-stdout.log", root)),
        "mineru" => Ok(format!("{}/backend/logs/mineru-api.log", root)),
        "web" => Ok(format!("{}/web/logs/desktop-stdout.log", root)),
        other => Err(format!("未知日志: {}（可选: backend / web / mineru）", other)),
    }
}

/// 启动实时日志流 — 在后台线程中 tail 日志文件，每隔 ~500ms 检查新内容并通过
/// `log-line` 事件推送到前端。同一服务的多次调用会创建多个线程（前端负责去重）。
#[tauri::command]
pub fn watch_log(
    service: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let root = project_root_str();
    let path = get_log_path(&service, &root)?;
    let svc = service.clone();

    std::thread::spawn(move || {
        // 尝试打开文件，如果不存在就等待（最多 40s）
        let mut attempts = 0;
        let mut file = loop {
            match std::fs::File::open(&path) {
                Ok(f) => break Some(f),
                Err(_) => {
                    attempts += 1;
                    if attempts > 80 { return; }
                    std::thread::sleep(Duration::from_millis(500));
                }
            }
        };

        // 从文件末尾开始 tail
        if let Some(ref mut f) = file {
            let _ = f.seek(SeekFrom::End(0));
        }

        loop {
            std::thread::sleep(Duration::from_millis(500));

            let f = match &mut file {
                Some(f) => f,
                None => {
                    if let Ok(new_f) = std::fs::File::open(&path) {
                        file = Some(new_f);
                        file.as_mut().unwrap()
                    } else { continue; }
                }
            };

            // 读取新增内容
            let mut buf = String::new();
            if f.read_to_string(&mut buf).is_err() || buf.is_empty() {
                continue;
            }
            for line in buf.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() { continue; }
                let _ = app.emit("log-line", LogLine {
                    service: svc.clone(),
                    line: trimmed.to_string(),
                });
            }
        }
    });

    Ok(())
}

#[tauri::command]
pub fn open_web_ui() -> Result<(), String> {
    let ports = get_ports();
    let url = format!("http://localhost:{}", ports.web);
    open_url(&url)
}

fn open_url(url: &str) -> Result<(), String> {
    #[cfg(windows)]
    {
        Command::new("cmd")
            .args(["/c", "start", "", url])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Command::new("xdg-open").arg(url).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(url).spawn().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub async fn run_ragctl(args: Vec<String>) -> Result<CmdOutput, String> {
    let root = project_root_str();
    let script = format!("{}/command/ragctl.js", root);
    let out = tokio::process::Command::new("node")
        .arg(&script)
        .args(&args)
        .current_dir(&root)
        .output()
        .await
        .map_err(|e| format!("运行 ragctl 失败: {}", e))?;
    Ok(CmdOutput {
        success: out.status.success(),
        stdout: String::from_utf8_lossy(&out.stdout).to_string(),
        stderr: String::from_utf8_lossy(&out.stderr).to_string(),
        exit_code: out.status.code(),
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  环境引导：依赖检查 + 一键安装 + 模型下载（零依赖项目也能拉起）
// ═══════════════════════════════════════════════════════════════════════

use tauri::Emitter;
use tokio::io::{AsyncBufReadExt, BufReader};

#[derive(Serialize, Clone)]
pub struct DepStatus {
    pub key: String,
    pub name: String,
    pub installed: bool,
    pub version: Option<String>,
    pub detail: String,
    pub installable: bool,
}

#[derive(Serialize, Clone)]
pub struct ProgressEvent {
    pub step: String,
    pub level: String, // info / warn / error / done
    pub msg: String,
}

fn emit_progress(app: &tauri::AppHandle, step: &str, level: &str, msg: &str) {
    let _ = app.emit(
        "progress",
        ProgressEvent {
            step: step.to_string(),
            level: level.to_string(),
            msg: msg.to_string(),
        },
    );
}

fn home_dir() -> Option<std::path::PathBuf> {
    #[cfg(windows)]
    {
        std::env::var_os("USERPROFILE").map(std::path::PathBuf::from)
    }
    #[cfg(not(windows))]
    {
        std::env::var_os("HOME").map(std::path::PathBuf::from)
    }
}

/// 富化 PATH：把 ~/.local/bin + ~/.cargo/bin 加到子进程 PATH（uv 引导装到 .local/bin，
/// 但 Tauri 主进程的 PATH 在启动时固定，不会自动包含它）。
fn enriched_path() -> String {
    let mut paths: Vec<String> = vec![];
    if let Ok(p) = std::env::var("PATH") {
        paths.push(p);
    }
    if let Some(h) = home_dir() {
        paths.push(h.join(".local").join("bin").to_string_lossy().to_string());
        paths.push(h.join(".cargo").join("bin").to_string_lossy().to_string());
    }
    // Windows 的 %PATH% 用 ; 分隔，POSIX 用 :
    if cfg!(windows) {
        paths.join(";")
    } else {
        paths.join(":")
    }
}

fn try_version(bin: &str) -> Option<String> {
    let o = Command::new(bin).arg("--version").output().ok()?;
    if o.status.success() {
        let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
        Some(s.lines().next().unwrap_or(&s).to_string())
    } else {
        None
    }
}

fn find_uv() -> Option<String> {
    if try_version("uv").is_some() {
        return Some("uv".to_string());
    }
    if let Some(h) = home_dir() {
        let cand = if cfg!(windows) {
            h.join(".local").join("bin").join("uv.exe")
        } else {
            h.join(".local").join("bin").join("uv")
        };
        let s = cand.to_string_lossy().to_string();
        if try_version(&s).is_some() {
            return Some(s);
        }
        // cargo bin fallback（uv 装到 ~/.cargo/bin 的情形）
        let cand2 = if cfg!(windows) {
            h.join(".cargo").join("bin").join("uv.exe")
        } else {
            h.join(".cargo").join("bin").join("uv")
        };
        let s2 = cand2.to_string_lossy().to_string();
        if try_version(&s2).is_some() {
            return Some(s2);
        }
    }
    None
}

// ── 各依赖检测 ──

async fn check_uv() -> DepStatus {
    if let Some(p) = find_uv() {
        let v = try_version(&p).unwrap_or_default();
        return DepStatus {
            key: "uv".into(),
            name: "uv (Astral 包管理)".into(),
            installed: true,
            version: Some(v),
            detail: p,
            installable: true,
        };
    }
    DepStatus {
        key: "uv".into(),
        name: "uv (Astral 包管理)".into(),
        installed: false,
        version: None,
        detail: "未安装 — 可一键安装（单二进制）".into(),
        installable: true,
    }
}

async fn check_python() -> DepStatus {
    // uv 管理的 python 优先（项目用 uv）
    if let Some(uv) = find_uv() {
        if let Ok(o) = Command::new(&uv)
            .args(["python", "list", "--only-installed"])
            .output()
        {
            let s = String::from_utf8_lossy(&o.stdout);
            if s.contains("3.12") || s.contains("3.13") {
                let line = s.lines().find(|l| l.contains("3.1")).unwrap_or("via uv");
                return DepStatus {
                    key: "python".into(),
                    name: "Python 3.12".into(),
                    installed: true,
                    version: Some(line.trim().to_string()),
                    detail: "uv 管理".into(),
                    installable: true,
                };
            }
        }
    }
    // 系统 python
    for bin in ["python", "python3"] {
        if let Some(v) = try_version(bin) {
            if v.contains("3.1") {
                return DepStatus {
                    key: "python".into(),
                    name: "Python 3.12".into(),
                    installed: true,
                    version: Some(v),
                    detail: "system".into(),
                    installable: true,
                };
            }
        }
    }
    DepStatus {
        key: "python".into(),
        name: "Python 3.12".into(),
        installed: false,
        version: None,
        detail: "未检测到（uv 可自动下载安装）".into(),
        installable: true,
    }
}

async fn check_node() -> DepStatus {
    if let Some(v) = try_version("node") {
        return DepStatus {
            key: "node".into(),
            name: "Node.js".into(),
            installed: true,
            version: Some(v),
            detail: "system（web/前端/Claude Code 需要）".into(),
            installable: false,
        };
    }
    DepStatus {
        key: "node".into(),
        name: "Node.js".into(),
        installed: false,
        version: None,
        detail: "未安装 — 需手动装 Node 18+（web/前端需要）".into(),
        installable: false,
    }
}

async fn check_docker() -> DepStatus {
    if let Some(v) = try_version("docker") {
        return DepStatus {
            key: "docker".into(),
            name: "Docker (Neo4j 图谱)".into(),
            installed: true,
            version: Some(v),
            detail: "图谱功能可选".into(),
            installable: false,
        };
    }
    DepStatus {
        key: "docker".into(),
        name: "Docker (Neo4j 图谱)".into(),
        installed: false,
        version: None,
        detail: "未安装 — 图谱功能可选".into(),
        installable: false,
    }
}

async fn check_submodules() -> DepStatus {
    let root = project_root_str();
    let be = format!("{}/backend/app/main.py", root);
    let we = format!("{}/web/package.json", root);
    let ok = Path::new(&be).exists() && Path::new(&we).exists();
    DepStatus {
        key: "submodules".into(),
        name: "Git 子模块 (backend/web)".into(),
        installed: ok,
        version: None,
        detail: if ok {
            "已初始化".into()
        } else {
            "未初始化（需 git submodule update --init --recursive）".into()
        },
        installable: true,
    }
}

async fn check_backend_deps() -> DepStatus {
    let root = project_root_str();
    let sub = if cfg!(windows) { "Scripts" } else { "bin" };
    let py = if cfg!(windows) { "python.exe" } else { "python" };
    let ok = Path::new(&format!("{}/backend/.venv/{}", root, sub))
        .join(py)
        .exists();
    DepStatus {
        key: "backend_deps".into(),
        name: "后端 Python 依赖".into(),
        installed: ok,
        version: None,
        detail: if ok {
            "backend/.venv 就绪".into()
        } else {
            "未安装（uv sync，含 torch/transformers/mineru）".into()
        },
        installable: true,
    }
}

async fn check_web_deps() -> DepStatus {
    let root = project_root_str();
    let ok = Path::new(&format!("{}/web/node_modules", root)).exists();
    DepStatus {
        key: "web_deps".into(),
        name: "前端依赖 (node_modules)".into(),
        installed: ok,
        version: None,
        detail: if ok {
            "web/node_modules 就绪".into()
        } else {
            "未安装（npm install）".into()
        },
        installable: true,
    }
}

async fn check_models_embedding() -> DepStatus {
    let root = project_root_str();
    let cfg = read_config_yml();
    let cache = cfg["embedding"]["cache_dir"]
        .as_str()
        .unwrap_or("./models_cache");
    let model = cfg["embedding"]["model_name"]
        .as_str()
        .unwrap_or("BAAI/bge-m3");
    let cache_path = if Path::new(cache).is_absolute() {
        cache.to_string()
    } else {
        format!("{}/{}", root, cache)
    };
    let hub = format!("{}/hub/models--{}", cache_path, model.replace('/', "--"));
    // 检查 snapshots 下是否有 >1GB 的 pytorch_model.bin
    let snap_dir = format!("{}/snapshots", hub);
    let mut ok = false;
    if let Ok(rd) = std::fs::read_dir(&snap_dir) {
        for e in rd.flatten() {
            if let Ok(sub) = std::fs::read_dir(e.path()) {
                for f in sub.flatten() {
                    if f.file_name() == "pytorch_model.bin"
                        && f.metadata().map(|m| m.len() > 1_000_000_000).unwrap_or(false)
                    {
                        ok = true;
                    }
                }
            }
        }
    }
    DepStatus {
        key: "models_embedding".into(),
        name: "Embedding 模型 (bge-m3)".into(),
        installed: ok,
        version: Some(model.to_string()),
        detail: if ok {
            "已缓存（~2.2GB）".into()
        } else {
            "未下载（~2.2GB，向量检索必需）".into()
        },
        installable: true,
    }
}

#[tauri::command]
pub async fn check_dependencies() -> Result<Vec<DepStatus>, String> {
    Ok(vec![
        check_uv().await,
        check_python().await,
        check_node().await,
        check_git().await,
        check_docker().await,
        check_submodules().await,
        check_backend_deps().await,
        check_web_deps().await,
        check_models_embedding().await,
        check_models_mineru().await,
        check_hf_endpoint().await,
    ])
}

async fn check_git() -> DepStatus {
    if let Some(v) = try_version("git") {
        return DepStatus {
            key: "git".into(),
            name: "Git (子模块管理)".into(),
            installed: true,
            version: Some(v),
            detail: "Git 可用于子模块初始化".into(),
            installable: false,
        };
    }
    DepStatus {
        key: "git".into(),
        name: "Git (子模块管理)".into(),
        installed: false,
        version: None,
        detail: "未安装 — 子模块请手动下载".into(),
        installable: false,
    }
}

/// 检查 MinerU PDF 解析模型是否已下载
async fn check_models_mineru() -> DepStatus {
    let be_cfg = read_backend_config_yml();
    let mineru_enabled = be_cfg["mineru"]["enabled"].as_bool().unwrap_or(false);

    if !mineru_enabled {
        return DepStatus {
            key: "models_mineru".into(),
            name: "MinerU OCR 模型".into(),
            installed: true,
            version: None,
            detail: "MinerU 已禁用（backend/config.yml: mineru.enabled=false）".into(),
            installable: false,
        };
    }

    // MinerU 模型通常下载到其默认缓存位置（~/.cache/modelscope/hub 或 ~/.cache/huggingface/hub）
    let home = if cfg!(windows) {
        std::env::var("USERPROFILE").unwrap_or_default()
    } else {
        std::env::var("HOME").unwrap_or_default()
    };
    let model_source = be_cfg["mineru"]["model_source"]
        .as_str()
        .unwrap_or("modelscope");

    // ModelScope 缓存路径
    let ms_hub = format!("{}/.cache/modelscope/hub", home);
    let hf_hub = format!("{}/.cache/huggingface/hub", home);

    let model_found = if model_source == "modelscope" {
        Path::new(&ms_hub).exists()
            && std::fs::read_dir(&ms_hub).map(|mut r| r.next().is_some()).unwrap_or(false)
    } else {
        Path::new(&hf_hub).exists()
            && std::fs::read_dir(&hf_hub).map(|mut r| r.next().is_some()).unwrap_or(false)
    };

    DepStatus {
        key: "models_mineru".into(),
        name: "MinerU OCR 模型".into(),
        installed: model_found,
        version: Some(model_source.to_string()),
        detail: if model_found {
            format!("模型源: {} — 已缓存", model_source)
        } else {
            format!(
                "模型源: {} — 未下载（首次解析 PDF 时自动下载，~2-5GB）",
                model_source
            )
        },
        installable: false, // MinerU 模型由 mineru-api 首次运行时自动下载
    }
}

/// 检查 HF_ENDPOINT / ModelScope 镜像配置
async fn check_hf_endpoint() -> DepStatus {
    let dotenv = read_dotenv();
    let hf_endpoint = dotenv.get("HF_ENDPOINT").cloned().unwrap_or_default();
    let using_mirror = hf_endpoint.contains("hf-mirror.com") || hf_endpoint.contains("modelscope");

    DepStatus {
        key: "hf_endpoint".into(),
        name: "模型下载镜像".into(),
        installed: !hf_endpoint.is_empty() || using_mirror,
        version: if hf_endpoint.is_empty() {
            Some("默认 hf-mirror.com".to_string())
        } else {
            Some(hf_endpoint.clone())
        },
        detail: if using_mirror {
            "✓ 使用国内镜像（下载更快）".into()
        } else if hf_endpoint.is_empty() {
            "默认 hf-mirror.com 镜像 — 国内下载快".into()
        } else {
            format!("直连: {}（海外用户可用）", hf_endpoint)
        },
        installable: false,
    }
}

// ── ensure_* 安装辅助 ──

async fn ensure_uv(app: &tauri::AppHandle) -> Result<String, String> {
    if let Some(p) = find_uv() {
        return Ok(p);
    }
    emit_progress(app, "uv", "info", "⏬ 安装 uv（Astral 官方安装器）...");
    #[cfg(windows)]
    let (prog, args): (&str, Vec<&str>) = (
        "powershell",
        vec![
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-c",
            "irm https://astral.sh/uv/install.ps1 | iex",
        ],
    );
    #[cfg(not(windows))]
    let (prog, args): (&str, Vec<&str>) = (
        "sh",
        vec!["-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
    );

    let out = tokio::process::Command::new(prog)
        .args(&args)
        .output()
        .await
        .map_err(|e| format!("启动安装器失败: {}", e))?;
    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let stderr = String::from_utf8_lossy(&out.stderr).to_string();
    if !stdout.is_empty() {
        for line in stdout.lines().take(10) {
            emit_progress(app, "uv", "info", line);
        }
    }
    if !out.status.success() {
        return Err(format!("uv 安装失败: {}", stderr));
    }
    // 标准安装位置通常即时可用
    if let Some(p) = find_uv() {
        emit_progress(app, "uv", "done", &format!("✓ uv 已安装: {}", p));
        return Ok(p);
    }
    Err(
        "uv 安装命令已执行但当前会话找不到 uv。请关闭并重开 Tauri（或手动把 ~/.local/bin 加 PATH）后重试"
            .into(),
    )
}

async fn ensure_python(uv: &str, app: &tauri::AppHandle) -> Result<(), String> {
    // 幂等检查
    if let Ok(o) = Command::new(uv)
        .args(["python", "list", "--only-installed"])
        .output()
    {
        let s = String::from_utf8_lossy(&o.stdout);
        if s.contains("3.12") || s.contains("3.13") {
            emit_progress(app, "python", "done", "🐍 Python 3.12 已就绪（uv 管理）");
            return Ok(());
        }
    }
    emit_progress(
        app,
        "python",
        "info",
        "🐍 下载 Python 3.12（uv python install，~30MB）...",
    );
    stream_command(app, "python", uv, &["python", "install", "3.12"], &project_root_str())
        .await?;
    emit_progress(app, "python", "done", "✓ Python 3.12 就绪");
    Ok(())
}

async fn ensure_submodules(app: &tauri::AppHandle) -> Result<String, String> {
    let root = project_root_str();
    emit_progress(app, "submodules", "info", "📦 初始化 git 子模块...");
    let out = tokio::process::Command::new("git")
        .args(["submodule", "update", "--init", "--recursive"])
        .current_dir(&root)
        .output()
        .await
        .map_err(|e| format!("git 启动失败: {}", e))?;
    let stderr = String::from_utf8_lossy(&out.stderr);
    for line in stderr.lines().take(8) {
        if !line.trim().is_empty() {
            emit_progress(app, "submodules", "info", line);
        }
    }
    if out.status.success() {
        emit_progress(app, "submodules", "done", "✓ 子模块就绪");
        Ok("子模块初始化完成".into())
    } else {
        Err(format!("git submodule 失败: {}", stderr))
    }
}

async fn download_embedding_model(app: &tauri::AppHandle) -> Result<String, String> {
    let uv = ensure_uv(app).await?;
    let root = project_root_str();
    // backend deps 必须先就绪（download_model 依赖 requests/requests）
    let be_venv = format!("{}/backend/.venv", root);
    if !Path::new(&be_venv).exists() {
        emit_progress(
            app,
            "models_embedding",
            "info",
            "首次运行：先安装后端依赖（uv sync）...",
        );
        stream_command(
            app,
            "backend_deps",
            &uv,
            &["sync"],
            &format!("{}/backend", root),
        )
        .await?;
    }
    emit_progress(
        app,
        "models_embedding",
        "info",
        "⏬ 下载 embedding 模型 bge-m3（~2.2GB，断点续传 + hf-mirror 镜像）...",
    );
    stream_command(
        app,
        "models_embedding",
        &uv,
        &["run", "python", "-m", "app.utils.download_model"],
        &format!("{}/backend", root),
    )
    .await?;
    emit_progress(app, "models_embedding", "done", "✓ bge-m3 已就绪");
    Ok("embedding 模型下载完成".into())
}

// 流式执行命令：stdout/stderr 行 → progress event
async fn stream_command(
    app: &tauri::AppHandle,
    step: &str,
    prog: &str,
    args: &[&str],
    cwd: &str,
) -> Result<(), String> {
    let mut child = tokio::process::Command::new(prog)
        .args(args)
        .current_dir(cwd)
        .env("PATH", enriched_path())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn {} 失败: {}（确认在 PATH）", prog, e))?;

    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();

    let app_o = app.clone();
    let step_o = step.to_string();
    tokio::spawn(async move {
        let mut reader = BufReader::new(stdout).lines();
        while let Ok(Some(line)) = reader.next_line().await {
            emit_progress(&app_o, &step_o, "info", &line);
        }
    });

    let app_e = app.clone();
    let step_e = step.to_string();
    tokio::spawn(async move {
        let mut reader = BufReader::new(stderr).lines();
        while let Ok(Some(line)) = reader.next_line().await {
            emit_progress(&app_e, &step_e, "warn", &line);
        }
    });

    let status = child
        .wait()
        .await
        .map_err(|e| format!("wait {} 失败: {}", step, e))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("{} 失败（exit {:?}）", step, status.code()))
    }
}

// ── 单项安装命令 ──

#[tauri::command]
pub async fn install_dependency(
    target: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    match target.as_str() {
        "uv" => ensure_uv(&app).await.map(|p| format!("uv 就绪: {}", p)),
        "python" => {
            let uv = ensure_uv(&app).await?;
            ensure_python(&uv, &app).await?;
            Ok("Python 3.12 就绪".into())
        }
        "submodules" => ensure_submodules(&app).await,
        "backend_deps" => {
            let uv = ensure_uv(&app).await?;
            let root = project_root_str();
            stream_command(&app, "backend_deps", &uv, &["sync"], &format!("{}/backend", root))
                .await?;
            Ok("后端依赖安装完成".into())
        }
        "web_deps" => {
            if try_version("node").is_none() {
                return Err("Node.js 未安装，无法 npm install。请先装 Node.js 18+".into());
            }
            let root = project_root_str();
            stream_command(&app, "web_deps", "npm", &["install"], &format!("{}/web", root))
                .await?;
            Ok("前端依赖安装完成".into())
        }
        "models_embedding" => download_embedding_model(&app).await,
        other => Err(format!("未知安装目标: {}（可选: uv/python/submodules/backend_deps/web_deps/models_embedding）", other)),
    }
}

// ── 一键引导：零依赖项目 → 全就绪 ──

#[tauri::command]
pub async fn bootstrap_all(app: tauri::AppHandle) -> Result<String, String> {
    let _ = app.emit("bootstrap", "start");
    emit_progress(
        &app,
        "bootstrap",
        "info",
        "🚀 开始一键引导（零依赖环境也能拉起）",
    );

    let uv = ensure_uv(&app).await?;
    emit_progress(&app, "bootstrap", "done", "✓ uv");

    ensure_python(&uv, &app).await?;
    emit_progress(&app, "bootstrap", "done", "✓ Python 3.12");

    let root = project_root_str();
    let be_main = format!("{}/backend/app/main.py", root);
    if !Path::new(&be_main).exists() {
        ensure_submodules(&app).await?;
    }
    emit_progress(&app, "bootstrap", "done", "✓ 子模块");

    stream_command(&app, "backend_deps", &uv, &["sync"], &format!("{}/backend", root)).await?;
    emit_progress(&app, "bootstrap", "done", "✓ 后端依赖（torch/transformers/mineru）");

    stream_command(
        &app,
        "models_embedding",
        &uv,
        &["run", "python", "-m", "app.utils.download_model"],
        &format!("{}/backend", root),
    )
    .await?;
    emit_progress(&app, "bootstrap", "done", "✓ Embedding 模型 bge-m3");

    if try_version("node").is_some() {
        if !Path::new(&format!("{}/web/node_modules", root)).exists() {
            stream_command(
                &app,
                "web_deps",
                "npm",
                &["install"],
                &format!("{}/web", root),
            )
            .await?;
        }
        emit_progress(&app, "bootstrap", "done", "✓ 前端依赖");
    } else {
        emit_progress(
            &app,
            "bootstrap",
            "warn",
            "⚠ Node.js 未装，跳过前端依赖（backend 可用，web 暂不可用）",
        );
    }

    emit_progress(
        &app,
        "bootstrap",
        "done",
        "🎉 全部就绪！现在可点「一键启动」",
    );
    let _ = app.emit("bootstrap", "done");
    Ok("引导完成".into())
}

// ═══════════════════════════════════════════════════════════════════════
//  配置可视化读写（config.yml + backend/config.yml + .env）
// ═══════════════════════════════════════════════════════════════════════

#[tauri::command]
pub fn read_config_full() -> Result<serde_json::Value, String> {
    let shared = read_config_yml();
    let backend_cfg = read_backend_config_yml();

    let mut result = serde_json::to_value(&shared).map_err(|e| e.to_string())?;

    // 合并 mineru（来自 backend/config.yml）
    if !backend_cfg["mineru"].is_null() {
        let mineru_json = serde_json::to_value(&backend_cfg["mineru"]).map_err(|e| e.to_string())?;
        if let serde_json::Value::Object(obj) = &mut result {
            obj.insert("mineru".to_string(), mineru_json);
        }
    }

    // 读 .env → _env 字段
    let env_path = format!("{}/.env", project_root_str());
    let mut env_map = serde_json::Map::new();
    if let Ok(content) = std::fs::read_to_string(&env_path) {
        for line in content.lines() {
            let l = line.trim();
            if l.is_empty() || l.starts_with('#') {
                continue;
            }
            if let Some(idx) = l.find('=') {
                let k = l[..idx].trim().to_string();
                let v = l[idx + 1..].trim().to_string();
                env_map.insert(k, serde_json::Value::String(v));
            }
        }
    }
    if let serde_json::Value::Object(obj) = &mut result {
        obj.insert("_env".to_string(), serde_json::Value::Object(env_map));
    }

    Ok(result)
}

/// 把 JSON 值转成 .env 字符串字面量（.env 全是字符串；前端可能把 "true"/数字转成了
/// bool/number，这里统一转回字符串，避免 as_str() 返回 None 导致写空值）。
fn env_val_to_string(v: &serde_json::Value) -> String {
    match v {
        serde_json::Value::Bool(b) => b.to_string(),
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::String(s) => s.clone(),
        _ => String::new(),
    }
}

#[tauri::command]
pub async fn save_config(
    config: serde_json::Value,
    app: tauri::AppHandle,
) -> Result<String, String> {
    let root = project_root_str();
    let obj = config
        .as_object()
        .ok_or("config 必须是对象")?
        .clone();

    // 分离 mineru（→ backend/config.yml）和 _env（→ .env），其余 → config.yml
    let mineru_val = obj.get("mineru").cloned();
    let env_val = obj.get("_env").cloned();

    let mut shared_obj = obj.clone();
    shared_obj.remove("mineru");
    shared_obj.remove("_env");

    // 写 config.yml（备份 .bak）
    let shared_path = format!("{}/config.yml", root);
    let _ = std::fs::copy(&shared_path, format!("{}.bak", shared_path));
    let shared_json = serde_json::Value::Object(shared_obj);
    let shared_yaml =
        serde_yaml::to_string(&shared_json).map_err(|e| format!("yaml 序列化失败: {}", e))?;
    std::fs::write(&shared_path, shared_yaml)
        .map_err(|e| format!("写 config.yml 失败: {}", e))?;

    // 写 backend/config.yml 的 mineru 段（保留其他段）
    if let Some(mineru) = mineru_val {
        let be_cfg_path = format!("{}/backend/config.yml", root);
        let mut be_cfg = read_backend_config_yml();
        let mineru_yaml =
            serde_yaml::to_value(&mineru).map_err(|e| format!("mineru yaml 失败: {}", e))?;
        if let serde_yaml::Value::Mapping(m) = &mut be_cfg {
            m.insert(serde_yaml::Value::String("mineru".into()), mineru_yaml);
        }
        let be_yaml = serde_yaml::to_string(&be_cfg).map_err(|e| e.to_string())?;
        std::fs::write(&be_cfg_path, be_yaml)
            .map_err(|e| format!("写 backend/config.yml 失败: {}", e))?;
    }

    // 写 .env
    if let Some(ev) = env_val {
        if let Some(env_obj) = ev.as_object() {
            let env_path = format!("{}/.env", root);
            let mut lines = vec![
                "# RAG Knowledge Platform - Environment Variables".into(),
                "# 由 Tauri 桌面控制台写入".into(),
                "# Env 优先级 > config.yml".into(),
                "".into(),
            ];
            // 已知 key 顺序（重要的先）
            let known = [
                "APP_MODE",
                "BACKEND_PORT",
                "WEB_PORT",
                "BACKEND_URL",
                "TREE_STORAGE_PATH",
                "HF_ENDPOINT",
                "NEO4J_PASSWORD",
                "KB_AUTH_TOKEN",
                "PYTHONUTF8",
            ];
            for k in known {
                if let Some(v) = env_obj.get(k) {
                    let vs = env_val_to_string(v);
                    if vs.is_empty() {
                        lines.push(format!("# {}=", k));
                    } else {
                        lines.push(format!("{}={}", k, vs));
                    }
                }
            }
            for (k, v) in env_obj {
                if known.contains(&k.as_str()) {
                    continue;
                }
                let vs = env_val_to_string(v);
                if vs.is_empty() {
                    lines.push(format!("# {}=", k));
                } else {
                    lines.push(format!("{}={}", k, vs));
                }
            }
            let _ = std::fs::copy(&env_path, format!("{}.bak", env_path));
            std::fs::write(&env_path, lines.join("\n"))
                .map_err(|e| format!("写 .env 失败: {}", e))?;
        }
    }

    // 热重载到运行中的 backend（best-effort）
    let ports = get_ports();
    let url = format!("http://localhost:{}/api/v1/config/reload", ports.backend);
    if let Ok(client) = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
    {
        if let Ok(r) = client.post(&url).send().await {
            if r.status().is_success() {
                emit_progress(&app, "config", "done", "✓ 配置已热重载到运行中的 backend");
            }
        }
    }

    Ok("配置已保存（config.yml + backend/config.yml + .env）".into())
}

// ═══════════════════════════════════════════════════════════════════════
//  Claude Code 检测（CLI 安装 + 配置 + 认证 + MCP + 能否启动）
// ═══════════════════════════════════════════════════════════════════════

#[derive(Serialize, Clone)]
pub struct ClaudeCodeStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub cli_path: Option<String>,
    pub config_found: bool,
    pub config_path: Option<String>,
    pub auth_method: String, // proxy / api_key / oauth / none
    pub base_url: Option<String>,
    pub default_mode: Option<String>,
    pub global_mcp_count: usize,
    pub project_mcp_count: usize,
    pub project_mcp_names: Vec<String>,
    pub can_start: bool,
    pub detail: String,
}

#[tauri::command]
pub async fn check_claude_code() -> Result<ClaudeCodeStatus, String> {
    // 1. claude CLI 检测（PATH + ~/.local/bin + ~/.cargo/bin）
    let mut installed = false;
    let mut version = None;
    let mut cli_path = None;
    let mut can_start = false;

    if let Some(v) = try_version("claude") {
        installed = true;
        version = Some(v);
        cli_path = Some("claude".into());
        can_start = true;
    } else if let Some(h) = home_dir() {
        let candidates: Vec<std::path::PathBuf> = if cfg!(windows) {
            vec![
                h.join(".local").join("bin").join("claude.exe"),
                h.join(".cargo").join("bin").join("claude.exe"),
            ]
        } else {
            vec![
                h.join(".local").join("bin").join("claude"),
                h.join(".cargo").join("bin").join("claude"),
            ]
        };
        for cand in candidates {
            let s = cand.to_string_lossy().replace('\\', "/");
            if let Some(v) = try_version(&s) {
                installed = true;
                version = Some(v);
                cli_path = Some(s);
                can_start = true;
                break;
            }
        }
    }

    // 2. ~/.claude/settings.json
    let mut config_found = false;
    let mut config_path = None;
    let mut settings: serde_json::Value = serde_json::Value::Null;
    if let Some(h) = home_dir() {
        let p = h.join(".claude").join("settings.json");
        config_path = Some(p.to_string_lossy().replace('\\', "/"));
        if let Ok(content) = std::fs::read_to_string(&p) {
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&content) {
                settings = v;
                config_found = true;
            }
        }
    }

    // 3. 认证方式分析
    let env_cfg = &settings["env"];
    let has_proxy = env_cfg["ANTHROPIC_AUTH_TOKEN"]
        .as_str()
        .map(|s| !s.is_empty())
        .unwrap_or(false);
    let base_url = env_cfg["ANTHROPIC_BASE_URL"]
        .as_str()
        .map(|s| s.to_string());
    let has_api_key_env = std::env::var("ANTHROPIC_API_KEY")
        .map(|s| !s.is_empty())
        .unwrap_or(false);
    let has_api_key_cfg = env_cfg["ANTHROPIC_API_KEY"]
        .as_str()
        .map(|s| !s.is_empty())
        .unwrap_or(false);

    let auth_method = if has_proxy {
        "proxy".to_string()
    } else if has_api_key_env || has_api_key_cfg {
        "api_key".to_string()
    } else if installed {
        "oauth".to_string()
    } else {
        "none".to_string()
    };

    // 4. MCP servers（全局 settings.json + 项目 .mcp.json）
    let global_mcp_count = settings["mcpServers"]
        .as_object()
        .map(|o| o.len())
        .unwrap_or(0);
    let (project_mcp_count, project_mcp_names) = {
        let root = project_root_str();
        let p = format!("{}/.mcp.json", root);
        let servers = std::fs::read_to_string(&p)
            .ok()
            .and_then(|c| serde_json::from_str::<serde_json::Value>(&c).ok())
            .and_then(|v| v["mcpServers"].as_object().cloned());
        match servers {
            Some(o) => (
                o.len(),
                o.keys().cloned().collect::<Vec<_>>(),
            ),
            None => (0, vec![]),
        }
    };

    let default_mode = settings["defaultMode"].as_str().map(|s| s.to_string());

    let detail = format!(
        "Claude Code {} | 认证: {}{} | MCP: 全局 {} + 项目 {} | 模式: {}",
        version.as_deref().unwrap_or("未安装"),
        auth_method,
        base_url
            .as_ref()
            .map(|u| format!(" ({})", u))
            .unwrap_or_default(),
        global_mcp_count,
        project_mcp_count,
        default_mode.as_deref().unwrap_or("default"),
    );

    Ok(ClaudeCodeStatus {
        installed,
        version,
        cli_path,
        config_found,
        config_path,
        auth_method,
        base_url,
        default_mode,
        global_mcp_count,
        project_mcp_count,
        project_mcp_names,
        can_start,
        detail,
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ ragctl 一体化集成：Rust 原生实现 → 零 Node 依赖，跨平台
// ═══════════════════════════════════════════════════════════════════════

/// Native ragctl check — same as `ragctl check` but runs inside Tauri (no node needed)
#[tauri::command]
pub async fn ragctl_check(_app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let deps = check_dependencies().await?;
    let ports = get_ports();

    #[derive(Serialize)]
    struct CheckSummary {
        deps: Vec<DepStatus>,
        backend_up: bool,
        web_up: bool,
        neo4j_up: bool,
        backend_port: u16,
        web_port: u16,
        project_root: String,
        app_mode: String,
    }

    let snap = check_status().await.unwrap_or(StatusSnapshot {
        backend: false, web: false, neo4j: false, mineru: false,
        backend_health: None, mineru_port: None,
        backend_url: String::new(), web_url: String::new(),
    });

    let summary = CheckSummary {
        deps,
        backend_up: snap.backend,
        web_up: snap.web,
        neo4j_up: snap.neo4j,
        backend_port: ports.backend,
        web_port: ports.web,
        project_root: project_root_str(),
        app_mode: read_app_mode(),
    };

    Ok(serde_json::to_value(&summary).unwrap_or_default())
}

/// Native ragctl deps — install all dependencies with real-time progress
#[tauri::command]
pub async fn ragctl_deps(app: tauri::AppHandle) -> Result<String, String> {
    emit_progress(&app, "deps", "info", "📦 开始安装所有依赖...");

    let uv = ensure_uv(&app).await?;
    emit_progress(&app, "deps", "done", "✓ uv");

    ensure_python(&uv, &app).await?;
    emit_progress(&app, "deps", "done", "✓ Python 3.12");

    let root = project_root_str();
    let be_main = format!("{}/backend/app/main.py", root);
    if !Path::new(&be_main).exists() {
        ensure_submodules(&app).await?;
        emit_progress(&app, "deps", "done", "✓ 子模块");
    }

    stream_command(&app, "deps_backend", &uv, &["sync"], &format!("{}/backend", root)).await?;
    emit_progress(&app, "deps", "done", "✓ Backend 依赖（torch/transformers/mineru）");

    if try_version("node").is_some() {
        if !Path::new(&format!("{}/web/node_modules", root)).exists() {
            stream_command(&app, "deps_web", "npm", &["install"], &format!("{}/web", root)).await?;
        }
        emit_progress(&app, "deps", "done", "✓ Web 依赖");
    } else {
        emit_progress(&app, "deps", "warn", "⚠ Node 未装，跳过 web 依赖");
    }

    // kb-mcp
    let mcp_dir = format!("{}/kb-mcp", root);
    if Path::new(&format!("{}/pyproject.toml", mcp_dir)).exists() {
        stream_command(&app, "deps_mcp", &uv, &["sync"], &mcp_dir).await?;
        emit_progress(&app, "deps", "done", "✓ kb-mcp 依赖");
    }

    emit_progress(&app, "deps", "done", "🎉 所有依赖安装完成");
    Ok("所有依赖安装完成".into())
}

/// Native ragctl model — pre-download BGE-M3 embedding model
#[tauri::command]
pub async fn ragctl_model(app: tauri::AppHandle) -> Result<String, String> {
    // Quick check if already downloaded
    if let Ok(deps) = check_dependencies().await {
        if deps.iter().any(|d| d.key == "models_embedding" && d.installed) {
            emit_progress(&app, "model", "done", "✓ BGE-M3 模型已缓存，跳过");
            return Ok("已缓存".into());
        }
    }

    emit_progress(&app, "model", "info", "⏬ 下载 BGE-M3 嵌入模型（~2.2GB，使用 hf-mirror 镜像...");
    download_embedding_model(&app).await?;
    emit_progress(&app, "model", "done", "✓ BGE-M3 就绪");
    Ok("模型下载完成".into())
}
