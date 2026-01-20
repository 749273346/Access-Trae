import pystray
from pystray import MenuItem as item
from PIL import Image
import subprocess
import sys
import os
import threading
import time
import webbrowser
import pyperclip
import requests
import logging
from typing import Optional, Tuple

SERVER_PORT = 18000
STREAMLIT_PORT = 8501
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
DASHBOARD_URL = f"http://localhost:{STREAMLIT_PORT}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "app_icon.png")
ICON_ICO_PATH = os.path.join(BASE_DIR, "assets", "app_icon.ico")
LOG_DIR = os.path.join(BASE_DIR, "logs")
ENV_PATH = os.path.join(BASE_DIR, ".env")
ENV_EXAMPLE_PATH = os.path.join(BASE_DIR, ".env.example")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "launcher.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

server_process = None
streamlit_process = None
is_running = False
server_log_handle = None
app_log_handle = None
icon_ref: Optional[pystray.Icon] = None
status_text = "🔴 服务离线"
status_detail = "Stopped"
shutdown_event = threading.Event()
_watchdog_last_restart_at = 0.0
_watchdog_lock = threading.Lock()
_server_started_at = 0.0
_ui_started_at = 0.0

def log(message):
    print(message)
    logging.info(message)

def start_services(icon=None, item=None):
    global server_process, streamlit_process, is_running, server_log_handle, app_log_handle, _server_started_at, _ui_started_at

    if (
        (_process_running(server_process) or _tcp_connectable("127.0.0.1", SERVER_PORT, timeout=0.3))
        and (_process_running(streamlit_process) or _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.3))
    ):
        is_running = True
        log("Services are already running.")
        _refresh_menu()
        return

    log("Starting services...")

    if server_log_handle is None:
        server_log_handle = open(os.path.join(LOG_DIR, "server.log"), "a", encoding="utf-8")
    if app_log_handle is None:
        app_log_handle = open(os.path.join(LOG_DIR, "app.log"), "a", encoding="utf-8")

    try:
        started_any = False

        if not _process_running(server_process) and not _tcp_connectable("127.0.0.1", SERVER_PORT, timeout=0.3):
            server_cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(SERVER_PORT)]
            server_process = subprocess.Popen(
                server_cmd,
                cwd=BASE_DIR,
                stdout=server_log_handle,
                stderr=server_log_handle,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            _server_started_at = time.time()
            log(f"Server started (PID: {server_process.pid})")
            started_any = True

        if not _process_running(streamlit_process) and not _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.3):
            app_cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(STREAMLIT_PORT), "--server.headless", "true"]
            streamlit_process = subprocess.Popen(
                app_cmd,
                cwd=BASE_DIR,
                stdout=app_log_handle,
                stderr=app_log_handle,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            _ui_started_at = time.time()
            log(f"Streamlit started (PID: {streamlit_process.pid})")
            started_any = True
        
        is_running = (
            _process_running(server_process)
            or _process_running(streamlit_process)
            or _tcp_connectable("127.0.0.1", SERVER_PORT, timeout=0.3)
            or _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.3)
        )
        if icon and started_any:
            icon.notify("Trae Services Started", "Trae Launcher")
        _refresh_menu()
            
    except Exception as e:
        log(f"Error starting services: {e}")
        if icon:
            icon.notify(f"Error: {e}", "Trae Launcher")
        _refresh_menu()

def stop_services(icon=None, item=None):
    global server_process, streamlit_process, is_running, server_log_handle, app_log_handle, _server_started_at, _ui_started_at

    log("Stopping services...")

    _terminate_process(streamlit_process)
    _terminate_process(server_process)
    streamlit_process = None
    server_process = None

    if server_log_handle:
        try:
            server_log_handle.close()
        except Exception:
            pass
        server_log_handle = None

    if app_log_handle:
        try:
            app_log_handle.close()
        except Exception:
            pass
        app_log_handle = None

    is_running = False
    _server_started_at = 0.0
    _ui_started_at = 0.0
    log("Services stopped.")
    if icon:
        icon.notify("Trae Services Stopped", "Trae Launcher")
    _refresh_menu()

def restart_services(icon, item):
    stop_services(icon)
    time.sleep(1)
    start_services(icon)

def open_dashboard(icon, item):
    webbrowser.open(DASHBOARD_URL)

def open_materials(icon, item):
    materials_path = os.path.join(BASE_DIR, "materials")
    if not os.path.exists(materials_path):
        os.makedirs(materials_path)
    os.startfile(materials_path)

def open_launcher_log(icon, item):
    _open_file(os.path.join(LOG_DIR, "launcher.log"))

def open_server_log(icon, item):
    _open_file(os.path.join(LOG_DIR, "server.log"))

def open_app_log(icon, item):
    _open_file(os.path.join(LOG_DIR, "app.log"))

def edit_config(icon, item):
    _ensure_env_file()
    _open_file(os.path.abspath(ENV_PATH))

def toggle_startup(icon, item):
    try:
        enabled = is_startup_enabled()
        set_startup_enabled(not enabled)
        icon.notify("已更新开机自启设置", "Trae Launcher")
    except Exception as e:
        log(f"Startup toggle error: {e}")
        icon.notify(f"开机自启设置失败: {e}", "Trae Launcher")
    _refresh_menu()

def clip_from_clipboard(icon, item):
    try:
        if not is_server_healthy(timeout=1.2):
            icon.notify("服务未就绪，请先启动服务", "Trae Launcher")
            return

        content = pyperclip.paste()
        if not content or not content.startswith("http"):
            icon.notify("Clipboard does not contain a valid URL.", "Trae Launcher")
            return

        log(f"Clipping from clipboard: {content}")
        icon.notify(f"Processing: {content[:30]}...", "Trae Launcher")
        
        response = requests.post(f"{SERVER_URL}/api/clip", json={"url": content, "mode": "raw"})
        
        if response.status_code == 200:
            icon.notify("✅ Task Queued Successfully!", "Trae Launcher")
        else:
            icon.notify(f"❌ Error: {response.status_code}", "Trae Launcher")
            
    except Exception as e:
        log(f"Clipboard clip error: {e}")
        icon.notify(f"Error: {e}", "Trae Launcher")

def on_exit(icon, item):
    shutdown_event.set()
    stop_services(icon)
    icon.stop()

def _open_file(path: str):
    try:
        if not os.path.exists(path):
            open(path, "a", encoding="utf-8").close()
        os.startfile(os.path.abspath(path))
    except Exception as e:
        log(f"Open file failed: {path} | {e}")

def _ensure_env_file():
    if os.path.exists(ENV_PATH):
        return
    if os.path.exists(ENV_EXAMPLE_PATH):
        with open(ENV_EXAMPLE_PATH, "r", encoding="utf-8") as src:
            content = src.read()
        with open(ENV_PATH, "w", encoding="utf-8") as dst:
            dst.write(content)
        return
    open(ENV_PATH, "a", encoding="utf-8").close()

def _process_running(proc) -> bool:
    try:
        return proc is not None and proc.poll() is None
    except Exception:
        return False

def _terminate_process(proc):
    if not _process_running(proc):
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

def _tcp_connectable(host: str, port: int, timeout: float = 0.8) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def is_server_healthy(timeout: float = 0.8) -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def is_dashboard_reachable(timeout: float = 0.8) -> bool:
    try:
        r = requests.get(DASHBOARD_URL, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False

def _compute_status() -> Tuple[str, str]:
    server_up = _process_running(server_process) and _tcp_connectable("127.0.0.1", SERVER_PORT, timeout=0.4)
    ui_up = _process_running(streamlit_process) and _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.4)
    if not server_up and not ui_up:
        return "🔴 服务离线", "Stopped"
    if is_server_healthy(timeout=0.8) and ui_up:
        return "🟢 系统正常", "All Systems Go"
    return "🟡 启动中", "Starting..."

def _refresh_menu():
    if icon_ref is None:
        return
    try:
        icon_ref.menu = build_menu()
    except Exception as e:
        log(f"Menu refresh failed: {e}")

def startup_shortcut_path() -> str:
    appdata = os.environ.get("APPDATA", "")
    startup_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    return os.path.join(startup_dir, "Trae Launcher.lnk")

def is_startup_enabled() -> bool:
    return os.path.exists(startup_shortcut_path())

def _pythonw_path() -> str:
    base = os.path.dirname(sys.executable)
    candidate = os.path.join(base, "pythonw.exe")
    if os.path.exists(candidate):
        return candidate
    return sys.executable

def _launcher_entry_for_startup() -> str:
    here = os.path.abspath(__file__)
    if here.lower().endswith(".py"):
        pyw = here[:-3] + ".pyw"
        if os.path.exists(pyw):
            return pyw
    return here

def set_startup_enabled(enabled: bool):
    lnk = startup_shortcut_path()
    os.makedirs(os.path.dirname(lnk), exist_ok=True)
    if not enabled:
        if os.path.exists(lnk):
            os.remove(lnk)
        return

    target = _pythonw_path()
    launcher_entry = _launcher_entry_for_startup()
    workdir = BASE_DIR
    icon_loc = os.path.abspath(ICON_ICO_PATH if os.path.exists(ICON_ICO_PATH) else ICON_PATH)

    def esc_ps_single(s: str) -> str:
        return s.replace("'", "''")

    args = f"\"{launcher_entry}\""
    ps = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{esc_ps_single(lnk)}'); "
        f"$Shortcut.TargetPath = '{esc_ps_single(target)}'; "
        f"$Shortcut.Arguments = '{esc_ps_single(args)}'; "
        f"$Shortcut.WorkingDirectory = '{esc_ps_single(workdir)}'; "
        f"$Shortcut.IconLocation = '{esc_ps_single(icon_loc)},0'; "
        "$Shortcut.Save();"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)

def regenerate_icon_action(icon, item):
    log("Regenerating icon...")
    try:
        script_path = os.path.join(BASE_DIR, "generate_icon.py")
        subprocess.run([sys.executable, script_path], check=True, cwd=BASE_DIR)
        
        if os.path.exists(ICON_PATH):
            new_image = Image.open(ICON_PATH)
            icon.icon = new_image
            
            if is_startup_enabled():
                set_startup_enabled(True)
                
            log("Icon updated successfully.")
            icon.notify("图标已更新", "Trae Launcher")
        else:
            log("Icon file not found after generation.")
            icon.notify("生成图标失败：文件未找到", "Trae Launcher")
    except Exception as e:
        log(f"Error regenerating icon: {e}")
        icon.notify(f"更新图标失败: {e}", "Trae Launcher")

def build_menu():
    can_open_dashboard = lambda _: is_server_healthy(timeout=0.6) and _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.4)
    can_clip = lambda _: is_server_healthy(timeout=0.6)
    can_restart = lambda _: _process_running(server_process) or _process_running(streamlit_process)

    logs_menu = pystray.Menu(
        item("启动器日志", open_launcher_log),
        item("Server 日志", open_server_log),
        item("App 日志", open_app_log),
    )

    services_menu = pystray.Menu(
        item("▶️ 启动服务", start_services, enabled=lambda _: not (_process_running(server_process) or _process_running(streamlit_process))),
        item("⏹️ 停止服务", stop_services, enabled=can_restart),
        item("🔄 重启服务", restart_services, enabled=can_restart),
    )

    system_menu = pystray.Menu(
        item("🚀 开机自启", toggle_startup, checked=lambda _: is_startup_enabled()),
        item("🎨 重新生成图标", regenerate_icon_action),
    )

    return pystray.Menu(
        item(lambda _: status_text, lambda icon, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        item("🌐 打开控制台", open_dashboard, enabled=can_open_dashboard),
        item("📋 剪贴板一键采集", clip_from_clipboard, enabled=can_clip),
        item("📂 打开素材库", open_materials),
        item("⚙️ 编辑配置 (.env)", edit_config),
        pystray.Menu.SEPARATOR,
        item("🛠️ 系统维护", system_menu),
        item("🧰 服务控制", services_menu),
        item("📝 查看日志", logs_menu),
        pystray.Menu.SEPARATOR,
        item("❌ 退出", on_exit),
    )

def main():
    global icon_ref, status_text, status_detail

    if "--self-test" in sys.argv:
        start_services()
        ok = _wait_for_ready(timeout_s=20)
        print(f"ready={ok}")
        if ok:
            r = requests.post(f"{SERVER_URL}/api/clip", json={"url": "https://example.com", "mode": "raw"}, timeout=3)
            print(f"clip_status={r.status_code}")
        stop_services()
        sys.exit(0 if ok else 2)

    if os.path.exists(ICON_PATH):
        image = Image.open(ICON_PATH)
    else:
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))

    icon = pystray.Icon("Trae Launcher", image, "Trae", menu=build_menu())
    icon_ref = icon

    def poll_status():
        global status_text, status_detail, is_running
        while not shutdown_event.is_set():
            try:
                if is_running and (not _process_running(server_process) or not _process_running(streamlit_process)):
                    is_running = _process_running(server_process) or _process_running(streamlit_process)
                new_text, new_detail = _compute_status()
                if new_text != status_text or new_detail != status_detail:
                    status_text = new_text
                    status_detail = new_detail
                    try:
                        icon.title = f"Trae Launcher - {status_detail}"
                    except Exception:
                        pass
                    _refresh_menu()
            except Exception as e:
                log(f"Status polling error: {e}")
            time.sleep(2)

    threading.Thread(target=poll_status, daemon=True).start()
    threading.Thread(target=_watchdog_loop, daemon=True).start()

    start_services(icon)

    log("Launcher ready. Check system tray.")
    icon.run()

def _wait_for_ready(timeout_s: int = 20) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if is_server_healthy(timeout=0.8) and _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.4):
            return True
        time.sleep(0.5)
    return False

def _watchdog_loop():
    global _watchdog_last_restart_at
    global server_process, streamlit_process
    global _server_started_at, _ui_started_at
    while not shutdown_event.is_set():
        try:
            if is_running:
                server_port_ok = _tcp_connectable("127.0.0.1", SERVER_PORT, timeout=0.4)
                ui_port_ok = _tcp_connectable("127.0.0.1", STREAMLIT_PORT, timeout=0.4)
                server_ok = server_port_ok and is_server_healthy(timeout=0.8)

                if _process_running(server_process) and not server_port_ok and _server_started_at and (time.time() - _server_started_at) > 15:
                    log("Watchdog: server process running but port not reachable, restarting server...")
                    _terminate_process(server_process)
                    server_process = None

                if _process_running(streamlit_process) and not ui_port_ok and _ui_started_at and (time.time() - _ui_started_at) > 15:
                    log("Watchdog: streamlit process running but port not reachable, restarting app...")
                    _terminate_process(streamlit_process)
                    streamlit_process = None

                if (not server_ok) or (not ui_port_ok):
                    now = time.time()
                    with _watchdog_lock:
                        if now - _watchdog_last_restart_at >= 8:
                            _watchdog_last_restart_at = now
                            log("Watchdog: detected service down, attempting to start missing services...")
                            start_services(icon_ref)
        except Exception as e:
            log(f"Watchdog error: {e}")
        time.sleep(3)

if __name__ == "__main__":
    main()
