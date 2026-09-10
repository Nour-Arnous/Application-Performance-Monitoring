# APM Monitoring Agent - Single file for both GUI and CLI modes.
# Supports both developers (CLI) and non-technical users (GUI).
import requests
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import argparse
import sys
import os
import configparser
import random



# CORE AGENT LOGIC (shared between GUI and CLI)
class APMAgent:
    """
    Core agent that sends performance metrics to the APM server.
    Used by both the GUI and the CLI modes.
    """

    def __init__(self, api_key, app_id, base_url="http://127.0.0.1:8000"):
        """
        Initialize the agent with an API key and application ID.
        The API key is stripped of any leading/trailing whitespace.
        """
        cleaned_key = api_key.strip()
        self.api_key = cleaned_key
        self.app_id = app_id
        self.base_url = base_url
        self.running = False
        self.headers = {
            "X-API-Key": cleaned_key,
            "Content-Type": "application/json"
        }

    def send_metric(self, response_time, request_count=0, error_count=0):
        """
        Send a single metric to the APM API.
        Returns True if the request was successful (HTTP 201), False otherwise.
        """
        data = {
            "application": self.app_id,
            "response_time": response_time,
            "request_count": request_count,
            "error_count": error_count
        }
        url = f"{self.base_url}/api/metrics/"
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=5)
            return response.status_code == 201
        except Exception as e:
            print(f"Error sending metric: {e}")
            return False

    def start_sending(self, interval=5):
        """
        Main loop: generates simulated metrics and sends them every
        `interval` seconds. This simulates real performance data.
        """
        self.running = True
        while self.running:
            # Simulate realistic metrics (in production, these would be real measurements)
            resp_time = round(random.uniform(0.3, 2.8), 2)
            req_count = random.randint(10, 250)
            err_count = random.randint(0, 4)

            self.send_metric(resp_time, req_count, err_count)
            time.sleep(interval)

    def stop(self):
        """Stop the monitoring loop gracefully."""
        self.running = False


# =====================================================================
# CONFIGURATION MANAGEMENT (saves/loads API key and app ID)
# =====================================================================
CONFIG_FILE = "agent_config.ini"


def load_config():
    """
    Load saved configuration from file.
    Ensures that app_id and interval are always positive (defaults to 1 and 5).
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'Agent' in config:
            app_id = config.getint('Agent', 'app_id', fallback=1)
            interval = config.getint('Agent', 'interval', fallback=5)
            return {
                'api_key': config.get('Agent', 'api_key', fallback=''),
                'app_id': app_id if app_id > 0 else 1,
                'interval': interval if interval > 0 else 5
            }
    return {'api_key': '', 'app_id': 1, 'interval': 5}


def save_config(api_key, app_id, interval):
    """Save the current configuration to a file for next launch."""
    config = configparser.ConfigParser()
    config['Agent'] = {
        'api_key': api_key,
        'app_id': str(app_id),
        'interval': str(interval)
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)


# =====================================================================
# GUI MODE (for non-technical users)
# =====================================================================
class AgentGUI:
    """
    Graphical user interface for the agent.
    Users can enter API key, app ID, interval, then start/stop monitoring.
    """

    def __init__(self, master):
        self.master = master
        master.title("APM Monitoring Agent")
        master.geometry("560x480")
        master.configure(bg='#f5f5f5')

        # Load saved configuration
        saved = load_config()
        self.api_key_var = tk.StringVar(value=saved['api_key'])
        self.app_id_var = tk.IntVar(value=saved['app_id'])
        self.interval_var = tk.IntVar(value=saved['interval'])
        self.agent = None
        self.thread = None

        # Validator: only allow positive integers (blocks negative signs and letters)
        vcmd = (master.register(self.validate_positive_int), '%P')

        # ----- API Key Entry Field -----
        ttk.Label(master, text="API Key:", font=('Arial', 10)).grid(
            row=0, column=0, padx=10, pady=10, sticky='w')

        self.api_key_entry = tk.Entry(
            master,
            textvariable=self.api_key_var,
            width=34,
            font=('Arial', 10),
            bg='white',
            relief='solid',
            bd=1
        )
        self.api_key_entry.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        # ----- Dedicated Paste Button (for reliability) -----
        self.paste_btn = ttk.Button(master, text="Paste", width=8, command=self.force_paste)
        self.paste_btn.grid(row=0, column=2, padx=5, pady=10, sticky='w')

        # ----- Right-Click Context Menu (Cut / Copy / Paste) -----
        self.context_menu = tk.Menu(master, tearoff=0)
        self.context_menu.add_command(
            label="Cut",
            command=lambda: self.api_key_entry.event_generate("<<Cut>>"))
        self.context_menu.add_command(
            label="Copy",
            command=lambda: self.api_key_entry.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Paste", command=self.force_paste)

        def show_context_menu(event):
            self.api_key_entry.focus_set()
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

        self.api_key_entry.bind("<Button-3>", show_context_menu)

        # ----- FIX: Explicitly bind Ctrl+V, Ctrl+C, Ctrl+X, Ctrl+A -----
        # This ensures keyboard shortcuts work even when Spinbox widgets
        # interfere with default Tkinter bindings on Windows.
        self.api_key_entry.bind("<Control-v>", lambda e: self.force_paste())
        self.api_key_entry.bind("<Control-V>", lambda e: self.force_paste())
        self.api_key_entry.bind(
            "<Control-c>",
            lambda e: self.api_key_entry.event_generate("<<Copy>>"))
        self.api_key_entry.bind(
            "<Control-x>",
            lambda e: self.api_key_entry.event_generate("<<Cut>>"))
        self.api_key_entry.bind(
            "<Control-a>",
            lambda e: self.api_key_entry.select_range(0, tk.END))

        # ----- Application ID (Spinbox with validation) -----
        ttk.Label(master, text="Application ID:", font=('Arial', 10)).grid(
            row=1, column=0, padx=10, pady=10, sticky='w')

        self.app_id_entry = ttk.Spinbox(
            master,
            from_=1,
            to=100,
            textvariable=self.app_id_var,
            width=10,
            validate='key',
            validatecommand=vcmd
        )
        self.app_id_entry.grid(row=1, column=1, padx=10, pady=10, sticky='w')

        # ----- Interval in Seconds (Spinbox with validation) -----
        ttk.Label(master, text="Interval (sec):", font=('Arial', 10)).grid(
            row=2, column=0, padx=10, pady=10, sticky='w')

        self.interval_entry = ttk.Spinbox(
            master,
            from_=1,
            to=60,
            textvariable=self.interval_var,
            width=10,
            validate='key',
            validatecommand=vcmd
        )
        self.interval_entry.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        # ----- Start / Stop Buttons -----
        self.start_btn = ttk.Button(
            master, text="Start Monitoring", command=self.start_monitoring)
        self.start_btn.grid(row=3, column=0, padx=10, pady=20)

        self.stop_btn = ttk.Button(
            master, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=3, column=1, padx=10, pady=20)

        # ----- Log Area -----
        ttk.Label(master, text="Log:", font=('Arial', 10)).grid(
            row=4, column=0, padx=10, pady=5, sticky='w')

        self.log_area = scrolledtext.ScrolledText(
            master, height=10, width=64, state='normal')
        self.log_area.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

        # ----- Status Bar -----
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            master,
            textvariable=self.status_var,
            relief=tk.SUNKEN
        ).grid(row=6, column=0, columnspan=3, sticky='we', padx=10, pady=5)

        # Handle window close event
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # -----------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------
    def validate_positive_int(self, value):
        """
        Callback that allows only positive integer input in Spinboxes.
        Blocks negative signs, letters, and symbols.
        """
        if value == "":
            return True
        return value.isdigit()

    def force_paste(self):
        """
        Directly read the clipboard and insert it into the API Key entry.
        Bypasses any blocked default bindings. Returns 'break' to prevent
        the default paste handler from duplicating the insertion.
        """
        try:
            self.api_key_entry.focus_set()
            clipboard_text = self.master.clipboard_get()
            try:
                # Delete currently selected text if any
                self.api_key_entry.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            self.api_key_entry.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            # Clipboard is empty or inaccessible
            pass
        return "break"  # prevents duplicated paste

    def log(self, msg):
        """Append a message to the log area and auto-scroll."""
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def update_status(self, msg):
        """Update the status bar text."""
        self.status_var.set(msg)

    # -----------------------------------------------------------------
    # Start / Stop Actions
    # -----------------------------------------------------------------
    def start_monitoring(self):
        """
        Validate inputs, then start monitoring in a background thread.
        Disables input fields to prevent changes during runtime.
        """
        api_key = self.api_key_var.get().strip()

        # Validate the numeric fields
        try:
            app_id = int(self.app_id_var.get())
            interval = int(self.interval_var.get())
            if app_id <= 0 or interval <= 0:
                raise ValueError()
        except (ValueError, tk.TclError):
            messagebox.showerror(
                "Error",
                "Application ID and Interval must be valid positive numbers!")
            return

        # Validate the API key
        if not api_key:
            messagebox.showerror("Error", "API Key is required!")
            return

        # Save config and start sending
        save_config(api_key, app_id, interval)
        self.log(f"Starting monitoring for Application ID: {app_id}")
        self.update_status("Running...")

        self.agent = APMAgent(api_key, app_id)
        self.thread = threading.Thread(
            target=self.agent.start_sending, args=(interval,), daemon=True)
        self.thread.start()

        # Disable input fields
        self.api_key_entry.config(state='disabled')
        self.app_id_entry.config(state='disabled')
        self.interval_entry.config(state='disabled')
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_monitoring(self):
        """
        Stop monitoring and re-enable input fields so the user can
        modify the API key or application ID again.
        """
        if self.agent:
            self.agent.stop()
        self.log("Monitoring stopped.")
        self.update_status("Stopped")

        # Re-enable inputs
        self.api_key_entry.config(state='normal')
        self.app_id_entry.config(state='normal')
        self.interval_entry.config(state='normal')
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def on_closing(self):
        """Stop the agent and close the window cleanly."""
        if self.agent:
            self.agent.stop()
        self.master.destroy()


# =====================================================================
# CLI MODE (for developers)
# =====================================================================
def run_cli():
    """
    Command-line interface for developers.
    Usage: agent_app.py --key YOUR_API_KEY --app-id 1 --interval 5
    """
    parser = argparse.ArgumentParser(description="APM Agent - CLI Mode")
    parser.add_argument("--key", required=True,
                        help="API Key from APM Dashboard")
    parser.add_argument("--app-id", type=int, required=True,
                        help="Application ID from Dashboard")
    parser.add_argument("--interval", type=int, default=5,
                        help="Send interval in seconds")

    args = parser.parse_args()

    # Validate CLI inputs
    if args.app_id <= 0:
        print("ERROR: Application ID must be a positive number.")
        sys.exit(1)
    if args.interval <= 0:
        print("ERROR: Interval must be a positive number.")
        sys.exit(1)
    if not args.key.strip():
        print("ERROR: API Key cannot be empty.")
        sys.exit(1)

    print(f"Starting APM Agent in CLI mode for App ID: {args.app_id}")
    agent = APMAgent(args.key, args.app_id)
    try:
        agent.start_sending(args.interval)
    except KeyboardInterrupt:
        agent.stop()
        print("\nAgent stopped gracefully.")


# =====================================================================
# ENTRY POINT (chooses GUI vs CLI based on arguments)
# =====================================================================
if __name__ == "__main__":
    # If any command-line argument is given, use CLI mode
    if len(sys.argv) > 1:
        run_cli()
    else:
        # Otherwise launch the GUI
        root = tk.Tk()
        app = AgentGUI(root)
        root.mainloop()