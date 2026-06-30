import os
import sys
import subprocess
import threading
import webbrowser
import time
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
# License check: validation runs before the GUI starts
try:
    from core.license import validate_or_exit
    validate_or_exit()
except SystemExit as e:
    root = tk.Tk()
    root.withdraw()
    msg = str(e) if str(e) else "This copy of the application is not licensed for this device."
    messagebox.showerror("License Verification", msg)
    sys.exit(1)
except Exception as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("License Verification Error", f"Failed to perform license check:\n{e}")
    sys.exit(1)


# ---------- Visual constants ----------
BG = "#0f1115"
PANEL = "#171a21"
PANEL_ALT = "#1d2129"
ACCENT = "#4f8cff"
ACCENT_HOVER = "#3f78e0"
GREEN = "#2ecc71"
RED = "#ff5c5c"
AMBER = "#f5a623"
TEXT_MAIN = "#e8eaed"
TEXT_DIM = "#8a8f98"
FONT = "Segoe UI"


class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("School ERP Server Controller")
        self.root.geometry("480x420")
        self.root.minsize(480, 420)
        self.root.configure(bg=BG)

        self.server_thread = None
        self.server_instance = None
        self.node_process = None
        self.browser_opened = False
        self.is_running = False

        self._build_style()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------- UI construction ----------
    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Card.TFrame", background=PANEL)
        style.configure("Root.TFrame", background=BG)

        style.configure(
            "Start.TButton",
            background=GREEN, foreground="#0b1f12",
            font=(FONT, 11, "bold"), padding=10, borderwidth=0,
        )
        style.map("Start.TButton",
                  background=[("disabled", "#2a3a30"), ("active", "#27ae60")],
                  foreground=[("disabled", "#5a6b60")])

        style.configure(
            "Stop.TButton",
            background=RED, foreground="#2a0a0a",
            font=(FONT, 11, "bold"), padding=10, borderwidth=0,
        )
        style.map("Stop.TButton",
                  background=[("disabled", "#3a2626"), ("active", "#e64545")],
                  foreground=[("disabled", "#6b5a5a")])

    def _build_ui(self):
        root_frame = tk.Frame(self.root, bg=BG)
        root_frame.pack(fill="both", expand=True, padx=18, pady=18)

        # --- Header ---
        header = tk.Frame(root_frame, bg=BG)
        header.pack(fill="x", pady=(0, 14))

        tk.Label(
            header, text="School ERP", font=(FONT, 16, "bold"),
            bg=BG, fg=TEXT_MAIN,
        ).pack(anchor="w")
        tk.Label(
            header, text="Local Server Controller", font=(FONT, 10),
            bg=BG, fg=TEXT_DIM,
        ).pack(anchor="w")

        # --- Status card ---
        status_card = tk.Frame(root_frame, bg=PANEL, padx=16, pady=14)
        status_card.pack(fill="x", pady=(0, 14))

        status_row = tk.Frame(status_card, bg=PANEL)
        status_row.pack(fill="x")

        self.status_dot = tk.Canvas(status_row, width=14, height=14, bg=PANEL, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 10))
        self._draw_dot(RED)

        status_text_frame = tk.Frame(status_row, bg=PANEL)
        status_text_frame.pack(side="left", fill="x", expand=True)

        self.status_label = tk.Label(
            status_text_frame, text="Stopped", font=(FONT, 13, "bold"),
            bg=PANEL, fg=TEXT_MAIN,
        )
        self.status_label.pack(anchor="w")

        self.status_sub = tk.Label(
            status_text_frame, text="Server is not running", font=(FONT, 9),
            bg=PANEL, fg=TEXT_DIM,
        )
        self.status_sub.pack(anchor="w")

        self.url_label = tk.Label(
            status_card, text="", font=(FONT, 9, "underline"),
            bg=PANEL, fg=ACCENT, cursor="hand2",
        )
        self.url_label.pack(anchor="w", pady=(8, 0))
        self.url_label.bind("<Button-1>", lambda e: webbrowser.open("http://127.0.0.1:8000"))

        # --- Buttons ---
        btn_row = tk.Frame(root_frame, bg=BG)
        btn_row.pack(fill="x", pady=(0, 14))

        self.start_btn = ttk.Button(
            btn_row, text="▶  Start Server", style="Start.TButton",
            command=self.start_services,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.stop_btn = ttk.Button(
            btn_row, text="■  Stop Server", style="Stop.TButton",
            command=self.stop_services, state=tk.DISABLED,
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # --- Log panel ---
        log_label = tk.Label(
            root_frame, text="ACTIVITY LOG", font=(FONT, 8, "bold"),
            bg=BG, fg=TEXT_DIM,
        )
        log_label.pack(anchor="w")

        log_frame = tk.Frame(root_frame, bg=PANEL_ALT)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(
            log_frame, bg=PANEL_ALT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
            font=("Consolas", 9), relief="flat", padx=10, pady=8,
            state="disabled", wrap="word",
        )
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self._log("Ready. Click \"Start Server\" to begin.")

    def _draw_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline="")

    def _log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    # ---------- State helpers ----------
    def _set_status(self, state):
        """state: 'starting' | 'running' | 'stopping' | 'stopped' | 'error'"""
        if state == "starting":
            self._draw_dot(AMBER)
            self.status_label.config(text="Starting…")
            self.status_sub.config(text="Launching background services")
            self.url_label.config(text="")
        elif state == "running":
            self._draw_dot(GREEN)
            self.status_label.config(text="Running")
            self.status_sub.config(text="Server is live")
            self.url_label.config(text="🔗 http://127.0.0.1:8000  (click to open)")
        elif state == "stopping":
            self._draw_dot(AMBER)
            self.status_label.config(text="Stopping…")
            self.status_sub.config(text="Shutting down services")
            self.url_label.config(text="")
        elif state == "stopped":
            self._draw_dot(RED)
            self.status_label.config(text="Stopped")
            self.status_sub.config(text="Server is not running")
            self.url_label.config(text="")
        elif state == "error":
            self._draw_dot(RED)
            self.status_label.config(text="Error")
            self.status_sub.config(text="Server failed to start — see log")
            self.url_label.config(text="")

    # ---------- Core logic (same behavior, now with logging/feedback) ----------
    def start_services(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._set_status("starting")
        self._log("Starting server…")

        if hasattr(sys, "frozen") or "nuitka" in sys.modules:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        service_dir = os.path.join(base_dir, 'whatsapp_service')
        
        try:
            self.node_process = subprocess.Popen(
                ["node", "server.js"],
                cwd=service_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self._log("WhatsApp automation service launched.")
        except Exception as e:
            self._log(f"WhatsApp service failed to launch: {e}")
            messagebox.showwarning("Warning", f"Failed to launch WhatsApp automation service:\n{e}")

        self.server_thread = threading.Thread(target=self.run_waitress, daemon=True)
        self.server_thread.start()

        threading.Thread(target=self.open_browser_delayed, daemon=True).start()

    def run_waitress(self):
        try:
            self.root.after(0, lambda: self._log("Loading Django & Waitress handlers..."))
            from waitress.server import create_server
            from django.contrib.staticfiles.handlers import StaticFilesHandler
            from school_erp.wsgi import application
            
            wsgi_app = StaticFilesHandler(application)
            self.server_instance = create_server(wsgi_app, host="127.0.0.1", port=8000)
            self.is_running = True
            self.root.after(0, lambda: self._set_status("running"))
            self.root.after(0, lambda: self._log("Waitress server bound to 127.0.0.1:8000."))
            self.server_instance.run()
        except Exception as e:
            self.root.after(0, lambda: self._log(f"Server error: {e}"))
            self.root.after(0, lambda: self._set_status("error"))
            self.root.after(0, lambda: messagebox.showerror("Server Error", f"Waitress server encountered an error:\n{e}"))
        finally:
            self.is_running = False
            self.root.after(0, self.update_ui_stopped)

    def open_browser_delayed(self):
        time.sleep(1.5)
        if self.server_instance:
            url = "http://127.0.0.1:8000"
            opened_fullscreen = False

            # Try launching popular browsers in fullscreen mode via subprocess on Windows
            if sys.platform == 'win32':
                import shutil
                # Paths or execution commands for common browsers
                browsers = [
                    {"cmd": "chrome", "flag": "--start-fullscreen"},
                    {"cmd": "msedge", "flag": "--start-fullscreen"},
                ]
                
                for browser in browsers:
                    if shutil.which(browser["cmd"]): # Check if browser exists in PATH
                        try:
                            subprocess.Popen([browser["cmd"], browser["flag"], url])
                            opened_fullscreen = True
                            self.root.after(0, lambda b=browser["cmd"]: self._log(f"Opened {b.upper()} in fullscreen."))
                            break
                        except Exception:
                            continue

            # Fallback if not Windows or if Chrome/Edge couldn't be launched directly
            if not opened_fullscreen:
                webbrowser.open(url)
                self.root.after(0, lambda: self._log(f"Opened default browser at {url}"))
                
            self.browser_opened = True

    def update_ui_stopped(self):
        self._set_status("stopped")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def stop_services(self):
        self.stop_btn.config(state=tk.DISABLED)
        self._set_status("stopping")
        self._log("Stopping server…")

        if self.node_process:
            try:
                self.node_process.terminate()
                self.node_process.wait(timeout=2)
                self._log("WhatsApp service stopped.")
            except subprocess.TimeoutExpired:
                self.node_process.kill()
                self._log("WhatsApp service force-killed (timeout).")
            except Exception as e:
                self._log(f"Error stopping WhatsApp service: {e}")
            self.node_process = None

        if self.server_instance:
            try:
                self.server_instance.close()
                self._log("Waitress server closed.")
            except Exception as e:
                self._log(f"Error closing server: {e}")
            self.server_instance = None

        if self.browser_opened and sys.platform == 'win32':
            try:
                subprocess.Popen("taskkill /im msedge.exe /f", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen("taskkill /im chrome.exe /f", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._log("Closed browser windows.")
            except Exception as e:
                self._log(f"Could not close browser: {e}")
            self.browser_opened = False

        self.update_ui_stopped()

    def on_closing(self):
        if self.is_running:
            if not messagebox.askokcancel("Quit", "The server is still running. Stop it and quit?"):
                return
            self.stop_services()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerApp(root)
    root.mainloop()