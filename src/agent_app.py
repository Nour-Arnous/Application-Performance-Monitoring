"""
APM Monitoring Agent - Single file for both GUI and CLI modes.
Supports both developers (CLI) and non-technical users (GUI).
"""
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

# Core Agent Logic (shared between GUI and CLI)
class APMAgent:
    """
    Core agent that sends performance metrics to the APM server.
    """
    def __init__(self, api_key, app_id, base_url="http://127.0.0.1:8000"):
        """
        Initialize the agent with API key and application ID.
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
        Returns True if successful, False otherwise.
        """
        data = {
            "application": self.app_id,
            "response_time": response_time,
            "request_count": request_count,
            "error_count": error_count
        }
        url = f"{self.base_url}/api/metrics/"
        try:
            # Print Header for checking
            print(f"Sending Headers: {self.headers}")
            print(f"Sending Data: {data}")
        
            response = requests.post(url, json=data, headers=self.headers, timeout=5)
        
            # Print Response
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
        
            return response.status_code == 201
        except Exception as e:
            print(f"Error sending metric: {e}")
            return False

    def start_sending(self, interval=5):
        """
        Main loop: generates simulated metrics and sends them every `interval` seconds.
        """
        self.running = True
        while self.running:
            # Simulate realistic metrics (replace with actual measurements in production)
            resp_time = round(random.uniform(0.3, 2.8), 2)
            req_count = random.randint(10, 250)
            err_count = random.randint(0, 4)
            
            success = self.send_metric(resp_time, req_count, err_count)
            if success:
                print(f"Sent: {resp_time}s, {req_count} req, {err_count} err")
            else:
                print(f"Failed to send metric")
            
            time.sleep(interval)

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False


# Configuration Management (save/load API key and app ID)
CONFIG_FILE = "agent_config.ini"

def load_config():
    """Load saved configuration from file."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'Agent' in config:
            return {
                'api_key': config.get('Agent', 'api_key', fallback=''),
                'app_id': config.getint('Agent', 'app_id', fallback=1),
                'interval': config.getint('Agent', 'interval', fallback=5)
            }
    return {'api_key': '', 'app_id': 1, 'interval': 5}

def save_config(api_key, app_id, interval):
    """Save configuration to file."""
    config = configparser.ConfigParser()
    config['Agent'] = {
        'api_key': api_key,
        'app_id': str(app_id),
        'interval': str(interval)
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

# GUI Mode (for non-technical users)
class AgentGUI:
    """
    Graphical user interface for the agent.
    Users can enter API key, app ID, interval, and start/stop monitoring.
    """
    def __init__(self, master):
        self.master = master
        master.title("APM Monitoring Agent")
        master.geometry("520x450")
        master.configure(bg='#f5f5f5')

        # Load saved configuration
        saved = load_config()
        self.api_key_var = tk.StringVar(value=saved['api_key'])
        self.app_id_var = tk.IntVar(value=saved['app_id'])
        self.interval_var = tk.IntVar(value=saved['interval'])
        self.agent = None
        self.thread = None

        # GUI Widgets 
        # API Key
        ttk.Label(master, text="API Key:", font=('Arial', 10)).grid(row=0, column=0, padx=10, pady=10, sticky='w')
        ttk.Entry(master, textvariable=self.api_key_var, width=45).grid(row=0, column=1, padx=10, pady=10)

        # Application ID (user can get this from Dashboard)
        ttk.Label(master, text="Application ID:", font=('Arial', 10)).grid(row=1, column=0, padx=10, pady=10, sticky='w')
        ttk.Spinbox(master, from_=1, to=100, textvariable=self.app_id_var, width=10).grid(row=1, column=1, padx=10, pady=10, sticky='w')

        # Interval (seconds)
        ttk.Label(master, text="Interval (sec):", font=('Arial', 10)).grid(row=2, column=0, padx=10, pady=10, sticky='w')
        ttk.Spinbox(master, from_=1, to=60, textvariable=self.interval_var, width=10).grid(row=2, column=1, padx=10, pady=10, sticky='w')

        # Buttons
        self.start_btn = ttk.Button(master, text="Start Monitoring", command=self.start_monitoring)
        self.start_btn.grid(row=3, column=0, padx=10, pady=20)

        self.stop_btn = ttk.Button(master, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=3, column=1, padx=10, pady=20)

        # Log display
        ttk.Label(master, text="Log:", font=('Arial', 10)).grid(row=4, column=0, padx=10, pady=5, sticky='w')
        self.log_area = scrolledtext.ScrolledText(master, height=10, width=60, state='normal')
        self.log_area.grid(row=5, column=0, columnspan=2, padx=10, pady=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=6, column=0, columnspan=2, sticky='we', padx=10, pady=5)

        # Save config when closing
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, msg):
        """Add a message to the log area."""
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def update_status(self, msg):
        """Update status bar."""
        self.status_var.set(msg)

    def start_monitoring(self):
        """Start the monitoring process in a separate thread."""
        api_key = self.api_key_var.get().strip()
        app_id = self.app_id_var.get()
        interval = self.interval_var.get()

        if not api_key:
            messagebox.showerror("Error", "API Key is required!")
            return

        # Save settings
        save_config(api_key, app_id, interval)

        self.log(f"Starting monitoring for Application ID: {app_id}")
        self.update_status("Running...")

        # Create agent instance
        self.agent = APMAgent(api_key, app_id)

        # Run in background thread to keep GUI responsive
        self.thread = threading.Thread(target=self.agent.start_sending, args=(interval,), daemon=True)
        self.thread.start()

        # Disable start button, enable stop button
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if self.agent:
            self.agent.stop()
        self.log("Monitoring stopped.")
        self.update_status("Stopped")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def on_closing(self):
        """Clean up before closing the window."""
        if self.agent:
            self.agent.stop()
        self.master.destroy()


# CLI Mode (for developers)
def run_cli():
    """
    Command-line interface for developers.
    Usage: agent_app.py --key YOUR_API_KEY --app-id 1 --interval 5
    """
    parser = argparse.ArgumentParser(description="APM Agent - CLI Mode")
    parser.add_argument("--key", required=True, help="API Key from APM Dashboard")
    parser.add_argument("--app-id", type=int, required=True, help="Application ID from Dashboard")
    parser.add_argument("--interval", type=int, default=5, help="Send interval in seconds")
    args = parser.parse_args()

    print(f"Starting APM Agent in CLI mode for App ID: {args.app_id}")
    agent = APMAgent(args.key, args.app_id)
    try:
        agent.start_sending(args.interval)
    except KeyboardInterrupt:
        agent.stop()
        print("\nAgent stopped gracefully.")



# Entry Point: Decide between GUI and CLI
if __name__ == "__main__":
    # If command-line arguments are provided, run in CLI mode
    if len(sys.argv) > 1:
        run_cli()
    else:
        # Otherwise, launch the GUI
        root = tk.Tk()
        app = AgentGUI(root)
        root.mainloop()