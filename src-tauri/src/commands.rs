// RAG Knowledge Desktop — Tauri 命令实现
//
// 所有命令都基于"项目根目录"（project_root）定位 backend/web/config。
// dev 模式 project_root = src-tauri 的父目录；打包后读 RAG_PROJECT_ROOT 环境变量。

use serde::Serialize;
use std::collections::HashMap;
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
}

#[derive(Serialize, Clone)]
pub struct Ports {
    pub backend: u16,
    pub web: u16,
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

pub fn get_ports() -> Ports {
    let cfg = read_config_yml();
    let mode = std::env::var("APP_MODE").unwrap_or_else(|_| "dev".to_string());
    let section = &cfg["server"][&mode];
    Ports {
        backend: section["backend_port"].as_u64().unwrap_or(BACKEND_PORT_DEFAULT as u64) as u16,
        web: section["frontend_port"].as_u64().unwrap_or(WEB_PORT_DEFAULT as u64) as u16,
    }
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

#[tauri::command]
pub fn detect_features() -> Result<Features, String> {
    let cfg = read_config_yml();
    let backend_cfg = read_backend_config_yml();
    let ports = get_ports();
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
    })
}

// ── 命令：服务启动 / 停止 ──

#[tauri::command]
pub async fn start_service(
    service: String,
    state: State<'_, AppState>,
) -> Result<ServiceResult, String> {
    let root = project_root_str();
    let res = match service.as_str() {
        "backend" => spawn_backend(&root)?,
        "web" => spawn_web(&root)?,
        "neo4j" => return start_neo4j(&root).await,
        "all" => {
            let mut b = spawn_backend(&root)?;
            // web 启动（失败则只报 backend）
            match spawn_web(&root) {
                Ok(w) => {
                    if let Some(pid) = w.pid {
                        state.pids.lock().unwrap().insert("web".into(), pid);
                        b.message.push_str(&format!("\n web pid={}", pid));
                    }
                }
                Err(e) => b.message.push_str(&format!("\n web 启动失败: {}", e)),
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

fn spawn_backend(root: &str) -> Result<ServiceResult, String> {
    let dir = format!("{}/backend", root);
    let log_dir = format!("{}/logs", dir);
    let _ = std::fs::create_dir_all(&log_dir);
    let stdout_path = format!("{}/desktop-stdout.log", log_dir);
    let out = std::fs::OpenOptions::new()
        .create(true).write(true).truncate(true)
        .open(&stdout_path)
        .map_err(|e| format!("无法写日志 {}: {}", stdout_path, e))?;
    let err = out.try_clone().map_err(|e| e.to_string())?;

    let child = Command::new("uv")
        .args(["run", "python", "main.py"])
        .current_dir(&dir)
        .env("APP_MODE", "dev")
        .env("PYTHONUTF8", "1")
        .stdout(Stdio::from(out))
        .stderr(Stdio::from(err))
        .spawn()
        .map_err(|e| format!("启动 uv 失败: {}（确认 uv 在 PATH）", e))?;

    let pid = child.id();
    std::mem::forget(child); // detach：进程随桌面 app 独立运行，不被 Drop 影响
    Ok(ServiceResult {
        success: true,
        message: format!(
            "Backend 启动中（uv run python main.py，cwd={}，pid={}，log={}）",
            dir, pid, stdout_path
        ),
        pid: Some(pid),
    })
}

fn spawn_web(root: &str) -> Result<ServiceResult, String> {
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
        .env("APP_MODE", "dev")
        .env("WEB_PORT", ports.web.to_string())
        .stdout(Stdio::from(out))
        .stderr(Stdio::from(err))
        .spawn()
        .map_err(|e| format!("启动 node 失败: {}（确认 node 在 PATH）", e))?;

    let pid = child.id();
    std::mem::forget(child);
    Ok(ServiceResult {
        success: true,
        message: format!(
            "Web 启动中（node start.mjs，cwd={}，pid={}，port={}）",
            dir, pid, ports.web
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
    let target = recorded.or(port_pid);

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
