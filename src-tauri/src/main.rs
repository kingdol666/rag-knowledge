#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .manage(commands::AppState::default())
        .invoke_handler(tauri::generate_handler![
            commands::project_root,
            commands::read_ports,
            commands::start_service,
            commands::stop_service,
            commands::check_status,
            commands::detect_features,
            commands::repair_service,
            commands::read_log_tail,
            commands::open_web_ui,
            commands::run_ragctl,
        ])
        .setup(|app| {
            #[cfg(debug_assertions)]
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.set_title("RAG Knowledge Platform — 控制台 [dev]");
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
