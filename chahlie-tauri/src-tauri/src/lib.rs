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

/// Locate the directory that contains the `chahlie/` Python package, so we can
/// run `python -m chahlie.tauri_server` with that dir on `PYTHONPATH`.
fn root_has_package(dir: &Path) -> bool {
    dir.join("chahlie/__init__.py").exists()
}

fn chahlie_root(app: &tauri::App) -> PathBuf {
    if let Ok(root) = std::env::var("CHAHLIE_ROOT") {
        let p = PathBuf::from(root);
        if root_has_package(&p) {
            return p;
        }
    }
    if let Ok(res) = app.path().resource_dir() {
        // Tauri rewrites `../` in resource paths to `_up_`, so a resource
        // declared as `../../chahlie` is bundled under
        // `<resource_dir>/_up_/_up_/chahlie`. Probe the likely depths.
        for sub in ["", "_up_/_up_", "_up_", "_up_/_up_/_up_"] {
            let candidate = if sub.is_empty() {
                res.clone()
            } else {
                res.join(sub)
            };
            if root_has_package(&candidate) {
                return candidate;
            }
        }
    }
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or(manifest)
}

/// Build a `Command` for an external Python interpreter with the AppImage's
/// injected environment scrubbed. The bundled AppRun runtime exports
/// `PYTHONHOME`, `PYTHONPATH` and `LD_LIBRARY_PATH` pointing inside the mounted
/// image; left in place they crash any *system* Python we spawn with
/// "No module named 'encodings'". Callers re-add `PYTHONPATH` when they need it.
fn py_command(program: &Path) -> Command {
    let mut cmd = Command::new(program);
    cmd.env_remove("PYTHONHOME");
    cmd.env_remove("PYTHONPATH");
    cmd.env_remove("PYTHONSTARTUP");
    cmd.env_remove("PYTHONEXECUTABLE");
    cmd.env_remove("LD_LIBRARY_PATH");
    cmd
}

fn python_runs(path: &Path) -> bool {
    // Use `-c import` rather than `--version`: a poisoned PYTHONHOME still lets
    // `--version` exit 0 while real imports fail, so version alone is a lie.
    py_command(path)
        .args(["-c", "import sys"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Packages the sidecar needs when no requirements file ships with the bundle.
const DEFAULT_PKGS: &[&str] = &[
    "fastapi",
    "uvicorn[standard]",
    "ollama",
    "anthropic",
    "rich",
    "python-dotenv",
    "requests",
    "click",
    "textual",
];

fn is_venv_python(python: &Path) -> bool {
    py_command(python)
        .args([
            "-c",
            "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn venv_python_path() -> Option<PathBuf> {
    dirs::home_dir().map(|h| h.join(".local/share/chahlie/venv/bin/python"))
}

/// Create the managed virtualenv on demand. A venv under $HOME sidesteps
/// read-only SteamOS system dirs and PEP 668 ("externally managed") errors,
/// which is the most common reason installs fail on the Deck.
fn ensure_venv() -> Option<PathBuf> {
    let py = venv_python_path()?;
    if python_runs(&py) {
        return Some(py);
    }
    let dir = py.parent()?.parent()?.to_path_buf();
    if let Some(parent) = dir.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let base = ["python3", "/usr/bin/python3"]
        .iter()
        .map(PathBuf::from)
        .find(|p| python_runs(p))?;
    let made = py_command(&base)
        .arg("-m")
        .arg("venv")
        .arg(&dir)
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    if !made {
        // Some distros ship a stripped venv module; allow system packages.
        let _ = py_command(&base)
            .arg("-m")
            .arg("venv")
            .arg("--system-site-packages")
            .arg(&dir)
            .status();
    }
    if python_runs(&py) {
        Some(py)
    } else {
        None
    }
}

fn python_candidates() -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();
    let mut push = |p: PathBuf| {
        if python_runs(&p) && !out.iter().any(|x| x == &p) {
            out.push(p);
        }
    };

    // 1. Explicit override always wins; don't build a venv we won't use.
    let explicit = std::env::var("CHAHLIE_PYTHON").ok();
    if let Some(py) = &explicit {
        push(PathBuf::from(py));
    }

    // 2. Managed venv (created on demand) — most reliable on the Steam Deck.
    //    Skip auto-creation when the user pinned their own interpreter.
    if explicit.is_none() {
        if let Some(venv) = ensure_venv() {
            push(venv);
        }
    } else if let Some(venv) = venv_python_path() {
        // Reuse an existing managed venv as a fallback, but don't create one.
        push(venv);
    }

    // 3. System interpreters as a fallback.
    push(PathBuf::from("python3"));
    push(PathBuf::from("/usr/bin/python3"));

    out
}

fn deps_installed(python: &Path) -> bool {
    py_command(python)
        .args(["-c", "import fastapi, uvicorn"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn run_pip(python: &Path, req: &Path, extra: &[&str]) -> bool {
    let mut cmd = py_command(python);
    cmd.args(["-m", "pip", "install", "--upgrade"]);
    for flag in extra {
        cmd.arg(flag);
    }
    if req.is_file() {
        cmd.arg("-r").arg(req);
    } else {
        cmd.args(DEFAULT_PKGS);
    }
    cmd.status().map(|s| s.success()).unwrap_or(false)
}

fn pip_install_deps(python: &Path, root: &Path) -> Result<(), String> {
    let req = root.join("requirements-tauri.txt");

    // Make sure pip itself exists (fresh venvs / minimal system pythons).
    let _ = py_command(python)
        .args(["-m", "ensurepip", "--upgrade"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();

    let ok = if is_venv_python(python) {
        // Inside a venv `--user` is invalid and break-system-packages is moot.
        run_pip(python, &req, &[])
    } else {
        // System Python: prefer a user install; fall back to PEP 668 override.
        run_pip(python, &req, &["--user"])
            || run_pip(python, &req, &["--user", "--break-system-packages"])
    };

    if !ok {
        return Err(
            "Could not install Python packages.\n\
             Run: bash scripts/install-tauri-deck.sh"
                .into(),
        );
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

    let child = py_command(python)
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

/// Set conservative WebKitGTK/GL rendering defaults before the webview boots.
///
/// On the Steam Deck (and some Mesa setups) WebKitGTK fails to create a GPU
/// context and aborts with `Could not create default EGL display:
/// EGL_BAD_PARAMETER`. Disabling the DMABUF renderer and falling back to
/// software GL sidesteps the broken EGL path entirely — fine for a chat UI.
/// Every value is only set when the user hasn't already exported their own,
/// so power users keep full control.
#[cfg(target_os = "linux")]
fn ensure_render_env() {
    let defaults = [
        ("WEBKIT_DISABLE_DMABUF_RENDERER", "1"),
        ("WEBKIT_DISABLE_COMPOSITING_MODE", "1"),
        // Software GL: slower but immune to the Deck's EGL_BAD_PARAMETER crash.
        ("LIBGL_ALWAYS_SOFTWARE", "1"),
    ];
    for (key, val) in defaults {
        if std::env::var_os(key).is_none() {
            std::env::set_var(key, val);
        }
    }
}

#[cfg(not(target_os = "linux"))]
fn ensure_render_env() {}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    ensure_render_env();

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
