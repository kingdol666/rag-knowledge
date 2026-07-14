#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .manage(commands::AppState::default())
        .invoke_handler(tauri::generate_handler![
            commands::project_root,
            commands::read_ports,
            commands::get_environment,
            commands::set_environment,
            commands::start_service,
            commands::stop_service,
            commands::stop_all_services,
            commands::check_status,
            commands::detect_features,
            commands::repair_service,
            commands::read_log_tail,
            commands::watch_log,
            commands::open_web_ui,
            commands::run_ragctl,
            commands::check_dependencies,
            commands::install_dependency,
            commands::bootstrap_all,
            commands::read_config_full,
            commands::save_config,
            commands::check_claude_code,
        ])
        .setup(|app| {
            #[cfg(debug_assertions)]
            if let Some(w) = app.get_webview_window("main") {
                let mode = commands::read_app_mode();
                let title = match mode.as_str() {
                    "prod" => "RAG Knowledge Platform — 控制台 [PROD]",
                    _ => "RAG Knowledge Platform — 控制台 [DEV]",
                };
                let _ = w.set_title(title);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
