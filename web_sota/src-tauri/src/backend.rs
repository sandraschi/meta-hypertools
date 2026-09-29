use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::str::FromStr;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Emitter, Manager};

pub struct BackendProcess(pub Mutex<Option<Child>>);

// -- PER-REPO: Customize these constants --
const BACKEND_NAME: &str = "meta-mcp-backend.exe";
const BACKEND_PORT: u16 = 10718;
const BACKEND_TAG: &str = "meta-mcp-backend-x86_64-pc-windows-msvc.exe";
const ENV_PORT: &str = "PORT";
const ENV_HOST: &str = "HOST";
const ENV_TAURI: &str = "META_MCP_TAURI";
// The real health/status route this backend serves - NOT a placeholder to
// leave as "/". port_holder_is_responsive hits this path specifically and
// requires an actual 200; a generic "/" or "any HTTP response" check would
// also pass for a process that's bound but stuck mid-init or 500ing on
// everything. Fill in this repo's real health endpoint before shipping.
const HEALTH_PATH: &str = "/health";

fn dev_backend_path() -> Option<PathBuf> {
    if !cfg!(debug_assertions) {
        return None;
    }
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(BACKEND_TAG);
    path.exists().then_some(path)
}

fn log_line(app: &AppHandle, message: &str) {
    eprintln!("[backend] {message}");
    if let Ok(dir) = app.path().app_log_dir() {
        let _ = fs::create_dir_all(&dir);
        let log_path = dir.join("backend-spawn.log");
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
            let _ = writeln!(file, "{message}");
        }
    }
}

fn resolve_bundled_backend(app: &AppHandle) -> Result<PathBuf, String> {
    let mut tried = Vec::new();

    if let Ok(path) = app.path().resolve(BACKEND_NAME, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() {
            return Ok(path);
        }
    }

    let resources_path = format!("resources/{BACKEND_NAME}");
    if let Ok(path) = app.path().resolve(&resources_path, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() {
            return Ok(path);
        }
    }

    if let Ok(dir) = app.path().executable_dir() {
        let path = dir.join("resources").join(BACKEND_NAME);
        tried.push(path.display().to_string());
        if path.exists() {
            return Ok(path);
        }
    }

    Err(format!("bundled backend missing from resources (tried: {})", tried.join("; ")))
}

fn install_dir_from_backend(path: &PathBuf) -> PathBuf {
    if let Some(parent) = path.parent() {
        if parent
            .file_name()
            .is_some_and(|name| name.eq_ignore_ascii_case("resources"))
        {
            if let Some(install_dir) = parent.parent() {
                return install_dir.to_path_buf();
            }
        }
        return parent.to_path_buf();
    }
    PathBuf::from(".")
}

pub fn materialize_backend(app: &AppHandle) -> Result<PathBuf, String> {
    if let Some(dev_path) = dev_backend_path() {
        log_line(app, &format!("using dev backend: {}", dev_path.display()));
        return Ok(dev_path);
    }

    let bundled = resolve_bundled_backend(app)?;
    log_line(app, &format!("using bundled backend: {}", bundled.display()));
    Ok(bundled)
}

/// True if the backend at 127.0.0.1:port answers HEALTH_PATH with HTTP 200
/// - i.e. is actually healthy, not just "a process is bound to this port"
/// or "something answered a request, any request."
///
/// A bare TCP connect isn't enough to justify skipping free_port: a hung or
/// crashing process can still hold the port open while answering nothing.
/// Hitting an arbitrary path and accepting any HTTP response isn't enough
/// either: a process wedged mid-startup, or one that 500s on everything,
/// would pass that check too. This hits HEALTH_PATH specifically and
/// requires the actual 200 status this app's health route returns on
/// success - fill in HEALTH_PATH above with the real one, not "/".
///
/// This is the check that was missing when free_port's image-name kill (see
/// its doc comment) was added: image-scoping stops it from killing
/// unrelated processes like Docker's wslrelay, but it still unconditionally
/// killed whatever `meta-mcp-backend`/`meta-mcp-native` process it found - which
/// is wrong whenever that process is a legitimate, shared, always-on
/// backend (an NSSM-managed service other MCP clients depend on staying up,
/// or simply this same app already running). free_port should still run,
/// unchanged, for a genuinely dead/hung holder - this only adds the "don't
/// kill something healthy just because it's there" check spawn_backend was
/// missing entirely.
fn port_holder_is_responsive(port: u16) -> bool {
    let addr = match ("127.0.0.1", port).to_socket_addrs() {
        Ok(mut addrs) => match addrs.next() {
            Some(addr) => addr,
            None => return false,
        },
        Err(_) => return false,
    };
    let mut stream = match TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
        Ok(s) => s,
        Err(_) => return false, // nothing listening at all
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(1500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
    let request = format!("GET {HEALTH_PATH} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false; // connected but can't even send - treat as a zombie
    }
    let mut buf = [0u8; 64];
    let n = match stream.read(&mut buf) {
        Ok(n) if n > 0 => n,
        _ => return false,
    };
    // Status line looks like "HTTP/1.1 200 OK\r\n..." - the second
    // whitespace-separated token is the status code.
    String::from_utf8_lossy(&buf[..n]).split_whitespace().nth(1) == Some("200")
}

/// Image-scoped kill + poll: kills only `meta-mcp-backend`/`meta-mcp-native`
/// processes, then polls up to 240s with a re-kill at 5s and a UAC-elevated
/// escalation at 15s if the port is still occupied.
///
/// Deliberately does NOT fall back to a blind port-PID kill
/// (`Get-NetTCPConnection -LocalPort {port} | taskkill /F /PID
/// $_.OwningProcess`) the way earlier versions of this template did - see
/// TAURI_PRODUCTION_PITFALLS.md, the wslrelay incident: that exact pattern
/// once killed Docker Desktop because its `wslrelay`/`com.docker.backend`
/// happened to be squatting the target port. If image-scoped killing
/// doesn't free the port, the right move is to fail loudly (spawn_backend
/// does, below) and let a human look, not escalate to killing an arbitrary
/// PID we can't identify.
///
/// `free_port` runs from *inside* the currently-running `meta-mcp-native`
/// process (spawn_backend is called from setup(), i.e. on the process's own
/// startup) — so a plain `Stop-Process -Name 'meta-mcp-native'` matches and
/// kills the caller itself (process-name matching has no "not me" concept).
/// Every native-image kill below excludes the caller's own PID for this
/// reason; the backend-image kill needs no such exclusion since
/// meta-mcp-backend.exe is always a distinct child process.
fn free_port(port: u16) -> bool {
    #[cfg(windows)]
    {
        let self_pid = std::process::id();
        let img_kill = format!(
            "Stop-Process -Name 'meta-mcp-backend' -Force -ErrorAction SilentlyContinue; \
             Get-Process -Name 'meta-mcp-native' -ErrorAction SilentlyContinue \
             | Where-Object {{ $_.Id -ne {self_pid} }} | Stop-Process -Force -ErrorAction SilentlyContinue; \
             taskkill /F /IM meta-mcp-backend.exe /T 2>$null; \
             Get-Process -Name 'meta-mcp-native' -ErrorAction SilentlyContinue \
             | Where-Object {{ $_.Id -ne {self_pid} }} \
             | ForEach-Object {{ taskkill /F /PID $_.Id /T 2>$null }}"
        );
        let _ = Command::new("powershell.exe")
            .args(["-NoProfile", "-Command", &img_kill])
            .stdout(Stdio::null()).stderr(Stdio::null())
            .status();

        let poll_script = format!(
            "if (Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue) {{ 1 }} else {{ 0 }}"
        );
        for i in 0..240 {
            let output = Command::new("powershell.exe")
                .args(["-NoProfile", "-Command", &poll_script])
                .stdout(Stdio::piped()).stderr(Stdio::null())
                .output();
            let occupied = output.ok().and_then(|o| {
                String::from_utf8(o.stdout).ok().and_then(|s| s.trim().parse::<u32>().ok())
            }).unwrap_or(1);
            if occupied == 0 {
                return true;
            }

            if i == 5 {
                let _ = Command::new("powershell.exe")
                    .args(["-NoProfile", "-Command", &img_kill])
                    .status();
            }
            if i == 15 {
                // Elevated retry is still image-scoped only - no blind
                // port-PID fallback here either, same reasoning as img_kill
                // above (TAURI_PRODUCTION_PITFALLS.md wslrelay incident).
                let elevated = format!(
                    "Start-Process powershell -Verb RunAs -WindowStyle Hidden -ArgumentList \
                     '-NoProfile -Command \"Stop-Process -Name meta-mcp-backend -Force -ErrorAction SilentlyContinue; \
                     taskkill /F /IM meta-mcp-backend.exe /T 2>$null\"'"
                );
                let _ = Command::new("powershell.exe")
                    .args(["-NoProfile", "-Command", &elevated])
                    .status();
            }
            thread::sleep(Duration::from_secs(1));
        }
        false
    }
    #[cfg(not(windows))]
    {
        true
    }
}

fn stop_managed_child(state: &BackendProcess) {
    if let Some(mut child) = state.0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

pub fn spawn_backend(app: AppHandle, state: &BackendProcess) -> Result<String, String> {
    stop_managed_child(state);

    // Attach to an already-healthy backend instead of killing it - see
    // port_holder_is_responsive's doc comment. A genuinely dead/hung
    // holder still gets killed below via free_port, unchanged. state.0 is
    // left None here, so RunEvent::Exit in main.rs correctly does NOT kill
    // a backend this instance never spawned.
    if port_holder_is_responsive(BACKEND_PORT) {
        log_line(
            &app,
            &format!("port 10718 already serving and responsive - attaching instead of spawning a second backend"),
        );
        return Ok(format!("Attached to existing backend on port 10718"));
    }

    if !free_port(BACKEND_PORT) {
        let msg = format!("Could not free port 10718 after 240s - TIME_WAIT not cleared");
        log_line(&app, &msg);
        return Err(msg);
    }

    let backend_path = materialize_backend(&app)?;
    let workdir = app
        .path()
        .executable_dir()
        .ok()
        .unwrap_or_else(|| install_dir_from_backend(&backend_path));

    log_line(
        &app,
        &format!("spawning {} (cwd {}) on port 10718",
            backend_path.display(), workdir.display()),
    );

    let mut command = Command::new(&backend_path);
    command
        .current_dir(&workdir)
        .env(ENV_PORT, BACKEND_PORT.to_string())
        .env(ENV_HOST, "127.0.0.1")
        .env(ENV_TAURI, "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command
        .spawn()
        .map_err(|e| format!("Failed to spawn {}: {e}", backend_path.display()))?;

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    state.0.lock().unwrap().replace(child);

    if let Some(out) = stdout {
        let app_handle = app.clone();
        thread::spawn(move || watch_backend_stream(out, app_handle));
    }
    if let Some(err) = stderr {
        let app_handle = app.clone();
        thread::spawn(move || watch_backend_stream(err, app_handle));
    }

    // Poll the backend TCP port to confirm it is actually listening. This is
    // the primary readiness signal (stdout text-matching in
    // watch_backend_stream is a secondary/faster signal but is fragile to
    // buffering and log-format changes; the TCP poll is authoritative).
    let addr = SocketAddr::from_str(&format!("127.0.0.1:10718")).unwrap();
    let app_health = app.clone();
    thread::spawn(move || {
        for attempt in 0..30 {
            thread::sleep(Duration::from_secs(2));
            match TcpStream::connect_timeout(&addr, Duration::from_secs(2)) {
                Ok(_) => {
                    log_line(&app_health, &format!(
                        "Backend health check PASSED on port 10718 (attempt {})", attempt + 1));
                    let _ = app_health.emit("backend-status", "ready");
                    return;
                }
                Err(e) => {
                    log_line(&app_health, &format!(
                        "Backend health check: {e} (attempt {})", attempt + 1));
                }
            }
        }
        log_line(&app_health, &format!(
            "Backend health check FAILED - not listening on port 10718 after 30 attempts"));
        let _ = app_health.emit("backend-status", "error: backend not reachable");
    });

    Ok(format!("Backend starting on port 10718"))
}

fn watch_backend_stream<R: std::io::Read + Send + 'static>(stream: R, app: AppHandle) {
    let reader = BufReader::new(stream);
    let mut ready = false;
    for line in reader.lines().map_while(Result::ok) {
        log_line(&app, &line);
        if !ready
            && (line.contains("Uvicorn running") || line.contains("Application startup complete"))
        {
            ready = true;
            let _ = app.emit("backend-status", "ready");
        }
    }
}
