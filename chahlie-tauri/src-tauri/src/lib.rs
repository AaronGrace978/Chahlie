//! Chahlie Tauri — spawn Python backend and expose API URL to the webview.

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::{Manager, RunEvent, State};

const DEFAULT_PORT: u16 = 18765;

struct BackendState {
    port: u16,
    child: Mutex<Option<Child>>,
}

fn chahlie_root(app: &tauri::App) -> PathBuf {
    if let Ok(root) = std::env::var("CHAHLIE_ROOT") {
        return PathBuf::from(root);
    }
    if let Ok(res) = app.path().resource_dir() {
        if res.join("chahlie/__init__.py").exists() {
            return res;
        }
    }
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or(manifest)
}

fn find_python() -> PathBuf {
    if let Ok(py) = std::env::var("CHAHLIE_PYTHON") {
        let path = PathBuf::from(py);
        if path.exists() {
            return path;
        }
    }
    if let Some(home) = dirs::home_dir() {
        let venv_py = home.join(".local/share/chahlie/venv/bin/python");
        if venv_py.exists() {
            return venv_py;
        }
    }
    PathBuf::from("python3")
}

fn health_ok(port: u16) -> bool {
    let mut stream = match TcpStream::connect(format!("127.0.0.1:{port}")) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let req = "GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = [0u8; 512];
    let Ok(n) = stream.read(&mut buf) else {
        return false;
    };
    let resp = String::from_utf8_lossy(&buf[..n]);
    resp.contains("200") && resp.contains("\"ok\":true")
}

fn wait_for_health(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{port}/health");
    for _ in 0..40 {
        if health_ok(port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    let _ = url; // kept for logging clarity in errors
    false
}

fn spawn_backend(root: &Path, port: u16) -> Result<Child, String> {
    let python = find_python();
    let mut cmd = Command::new(&python);
    cmd.arg("-m")
        .arg("chahlie.tauri_server")
        .arg("--port")
        .arg(port.to_string())
        .arg("--host")
        .arg("127.0.0.1")
        .current_dir(root)
        .env("PYTHONPATH", root)
        .env(
            "CHAHLIE_ENV_FILE",
            std::env::var("CHAHLIE_ENV_FILE").unwrap_or_else(|_| {
                dirs::home_dir()
                    .map(|h| {
                        h.join(".local/share/chahlie/.env")
                            .to_string_lossy()
                            .into_owned()
                    })
                    .unwrap_or_default()
            }),
        )
        .stdout(Stdio::null())
        .stderr(Stdio::piped());

    let child = cmd.spawn().map_err(|e| {
        format!(
            "Failed to start Python backend ({python:?}): {e}\n\
             Install deps: pip install -r requirements-tauri.txt"
        )
    })?;

    if !wait_for_health(port) {
        return Err(
            "Chahlie backend did not start. Run:\n  \
             pip install -r requirements-tauri.txt"
                .into(),
        );
    }

    Ok(child)
}

fn stop_backend(state: &BackendState) {
    if let Ok(mut guard) = state.child.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[tauri::command]
fn backend_url(state: State<'_, BackendState>) -> String {
    format!("http://127.0.0.1:{}", state.port)
}

#[tauri::command]
fn chahlie_data_dir() -> String {
    dirs::home_dir()
        .map(|h| h.join(".local/share/chahlie").to_string_lossy().into_owned())
        .unwrap_or_else(|| "~/.local/share/chahlie".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port = std::env::var("CHAHLIE_TAURI_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(DEFAULT_PORT);

    let backend_state = BackendState {
        port,
        child: Mutex::new(None),
    };

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(backend_state)
        .invoke_handler(tauri::generate_handler![backend_url, chahlie_data_dir])
        .setup(move |app| {
            let root = chahlie_root(app);
            let state = app.state::<BackendState>();
            match spawn_backend(&root, port) {
                Ok(child) => {
                    if let Ok(mut guard) = state.child.lock() {
                        *guard = Some(child);
                    }
                }
                Err(err) => {
                    eprintln!("{err}");
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit) {
            if let Some(state) = app_handle.try_state::<BackendState>() {
                stop_backend(&state);
            }
        }
    });
}
