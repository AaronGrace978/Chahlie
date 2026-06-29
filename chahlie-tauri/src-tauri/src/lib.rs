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
    startup_error: Mutex<Option<String>>,
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

fn python_runs(path: &Path) -> bool {
    Command::new(path)
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn python_candidates() -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();
    let mut push = |p: PathBuf| {
        if !out.iter().any(|x| x == &p) {
            out.push(p);
        }
    };

    if let Ok(py) = std::env::var("CHAHLIE_PYTHON") {
        push(PathBuf::from(py));
    }

    // AppImage / Steam Deck: system Python is most reliable.
    if std::env::var("APPIMAGE").is_ok() {
        push(PathBuf::from("/usr/bin/python3"));
        push(PathBuf::from("python3"));
    }

    push(PathBuf::from("python3"));
    push(PathBuf::from("/usr/bin/python3"));

    if let Some(home) = dirs::home_dir() {
        push(home.join(".local/share/chahlie/venv/bin/python"));
    }

    out.retain(|p| python_runs(p));
    out
}

fn deps_installed(python: &Path) -> bool {
    Command::new(python)
        .args(["-c", "import fastapi, uvicorn"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn pip_install_deps(python: &Path, root: &Path) -> Result<(), String> {
    let req = root.join("requirements-tauri.txt");
    let mut cmd = Command::new(python);
    cmd.args(["-m", "pip", "install", "--user", "--upgrade"]);
    if req.is_file() {
        cmd.arg("-r").arg(&req);
    } else {
        cmd.args([
            "fastapi",
            "uvicorn[standard]",
            "ollama",
            "anthropic",
            "rich",
            "python-dotenv",
            "requests",
            "click",
            "textual",
        ]);
    }
    // SteamOS Python 3.13+
    cmd.arg("--break-system-packages");

    let status = cmd
        .status()
        .map_err(|e| format!("pip install failed: {e}"))?;
    if !status.success() {
        // Retry without break-system-packages for older distros.
        let mut retry = Command::new(python);
        retry.args(["-m", "pip", "install", "--user", "--upgrade"]);
        if req.is_file() {
            retry.arg("-r").arg(&req);
        } else {
            retry.args([
                "fastapi",
                "uvicorn[standard]",
                "ollama",
                "anthropic",
                "rich",
                "python-dotenv",
                "requests",
                "click",
                "textual",
            ]);
        }
        if !retry.status().map(|s| s.success()).unwrap_or(false) {
            return Err(
                "Could not install Python packages.\n\
                 Run: bash scripts/install-tauri-deck.sh"
                    .into(),
            );
        }
    }
    Ok(())
}

fn ensure_python_deps(python: &Path, root: &Path) -> Result<(), String> {
    if deps_installed(python) {
        return Ok(());
    }
    eprintln!("Chahlie: installing Python dependencies (one time)…");
    pip_install_deps(python, root)?;
    if !deps_installed(python) {
        return Err(
            "Python deps still missing after install.\n\
             Run: bash scripts/install-tauri-deck.sh"
                .into(),
        );
    }
    Ok(())
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
    for _ in 0..40 {
        if health_ok(port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    false
}

fn try_spawn(python: &Path, root: &Path, port: u16) -> Result<Child, String> {
    ensure_python_deps(python, root)?;

    let child = Command::new(python)
        .arg("-m")
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
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn failed ({python:?}): {e}"))?;

    if !wait_for_health(port) {
        return Err(format!(
            "Backend did not respond on port {port} (python: {python:?})"
        ));
    }
    Ok(child)
}

fn spawn_backend(root: &Path, port: u16) -> Result<Child, String> {
    let candidates = python_candidates();
    if candidates.is_empty() {
        return Err(
            "No working python3 found.\n\
             Install: sudo pacman -S python python-pip"
                .into(),
        );
    }

    let mut errors: Vec<String> = Vec::new();
    for python in &candidates {
        match try_spawn(python, root, port) {
            Ok(child) => return Ok(child),
            Err(e) => errors.push(format!("  {python:?}: {e}")),
        }
    }

    Err(format!(
        "Could not start Chahlie Python backend.\n{}\n\n\
         Steam Deck fix — run in Konsole:\n  \
         bash scripts/install-tauri-deck.sh\n  \
         export WEBKIT_DISABLE_DMABUF_RENDERER=1\n  \
         export CHAHLIE_PYTHON=/usr/bin/python3\n  \
         ./Chahlie_*_amd64.AppImage",
        errors.join("\n")
    ))
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
fn backend_error(state: State<'_, BackendState>) -> Option<String> {
    state.startup_error.lock().ok()?.clone()
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
        startup_error: Mutex::new(None),
    };

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(backend_state)
        .invoke_handler(tauri::generate_handler![
            backend_url,
            backend_error,
            chahlie_data_dir
        ])
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
                    if let Ok(mut guard) = state.startup_error.lock() {
                        *guard = Some(err);
                    }
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
