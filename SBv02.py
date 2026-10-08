import tkinter as tk
from tkinter import messagebox, font, ttk
import time
import json
import os
import math
from datetime import datetime

# --- STANDARD KONFIGURASJON ---
DEFAULT_SETTINGS = {
    "hourly_wage": 100.0,
    "base_apy": 0.25,      # 25%
    "plus_apy": 1.00,      # 100%
    "use_plus_yield": False
}

YIELD_CUTOFF_SECONDS = 24 * 60 * 60  # 24 timer
DATA_FILE = "studybank_data.json"
UPDATE_INTERVAL_MS = 100  # 10 updates per sekund

class StudyBankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StudyBank Pro")
        self.root.geometry("450x600")
        self.root.configure(bg="#f0f2f5")

        # -- STATE --
        self.balance = 0.0
        self.total_yield = 0.0
        self.is_working = False
        
        self.current_session_start = None
        self.last_work_timestamp = None
        self.last_calc_time = time.time()
        
        self.sessions = []
        self.settings = DEFAULT_SETTINGS.copy()

        # Last inn data
        self.load_data()

        # -- UI OPPSETT --
        self.setup_ui()
        
        # Start loopen
        self.update_loop()

    def setup_ui(self):
        # Fonter
        title_font = font.Font(family="Helvetica", size=14, weight="bold")
        balance_font = font.Font(family="Courier", size=28, weight="bold")
        self.status_font = font.Font(family="Helvetica", size=10)

        # Header
        header_frame = tk.Frame(self.root, bg="#1e293b", pady=15)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="STUDY BANK", bg="#1e293b", fg="white", font=title_font).pack()
        
        # Innstillinger-knapp i header
        btn_settings = tk.Button(header_frame, text="⚙ Settings", command=self.open_settings, 
                                 bg="#334155", fg="white", relief="flat", font=("Helvetica", 8))
        btn_settings.place(relx=0.95, rely=0.5, anchor="e")

        # History-knapp i header
        btn_history = tk.Button(header_frame, text="📜 History", command=self.open_history, 
                                bg="#334155", fg="white", relief="flat", font=("Helvetica", 8))
        btn_history.place(relx=0.05, rely=0.5, anchor="w")

        # Balance Card
        self.balance_frame = tk.Frame(self.root, bg="white", padx=20, pady=20, relief="flat")
        self.balance_frame.pack(pady=20, padx=20, fill="x")
        
        tk.Label(self.balance_frame, text="Total Net Worth", bg="white", fg="#64748b", font=("Helvetica", 10)).pack()
        self.lbl_balance = tk.Label(self.balance_frame, text="kr 0,00", bg="white", fg="#0f172a", font=balance_font)
        self.lbl_balance.pack(pady=5)

        # Yield Status
        self.lbl_yield_status = tk.Label(self.balance_frame, text="Yield: Inactive", bg="white", fg="#ef4444", font=("Helvetica", 9, "bold"))
        self.lbl_yield_status.pack()

        # Info Grid (Lønn + Rente innstillinger visning)
        info_frame = tk.Frame(self.root, bg="#f0f2f5")
        info_frame.pack(pady=5)
        self.lbl_info_wage = tk.Label(info_frame, text=f"Wage: {self.settings['hourly_wage']} kr/h", bg="#f0f2f5", fg="#64748b", font=("Helvetica", 8))
        self.lbl_info_wage.pack(side="left", padx=10)

        # Session Status
        self.lbl_session_status = tk.Label(self.root, text="Ready to work?", bg="#f0f2f5", fg="#64748b", font=self.status_font)
        self.lbl_session_status.pack(pady=20)

        # Kontrollknapper
        btn_frame = tk.Frame(self.root, bg="#f0f2f5")
        btn_frame.pack(pady=10)

        self.btn_start = tk.Button(btn_frame, text="START SESSION", command=self.start_session, 
                                   bg="#10b981", fg="white", font=("Helvetica", 12, "bold"), 
                                   width=15, height=2, relief="flat", activebackground="#059669")
        self.btn_start.pack(pady=5)

        self.btn_stop = tk.Button(btn_frame, text="STOP SESSION", command=self.stop_session, 
                                  bg="#ef4444", fg="white", font=("Helvetica", 12, "bold"), 
                                  width=15, height=2, relief="flat", activebackground="#dc2626")
        
    def format_currency(self, amount):
        return f"kr {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # --- ACTION HANDLERS ---

    def start_session(self):
        self.is_working = True
        self.current_session_start = time.time()
        self.last_work_timestamp = time.time() 
        
        self.btn_start.pack_forget()
        self.btn_stop.pack(pady=5)
        self.lbl_session_status.config(text="🔥 Session Active!", fg="#10b981")
        self.save_data()

    def stop_session(self):
        now = time.time()
        duration = now - self.current_session_start
        
        # Beregn inntjening for denne økten for logging
        wage_per_sec = self.settings['hourly_wage'] / 3600.0
        earnings = duration * wage_per_sec
        
        # Loggfør økten
        self.sessions.append({
            "timestamp": now,
            "duration": duration,
            "earnings": earnings,
            "type": "Session"
        })

        self.is_working = False
        self.current_session_start = None
        self.last_work_timestamp = now 
        
        self.btn_stop.pack_forget()
        self.btn_start.pack(pady=5)
        self.lbl_session_status.config(text=f"Session ended. Earned {self.format_currency(earnings)}", fg="#64748b")
        self.save_data()

    def manual_log(self, hours, minutes):
        try:
            h = float(hours)
            m = float(minutes)
        except ValueError:
            return

        duration_sec = (h * 3600) + (m * 60)
        if duration_sec <= 0:
            return

        wage_per_sec = self.settings['hourly_wage'] / 3600.0
        earnings = duration_sec * wage_per_sec
        
        self.balance += earnings
        self.last_work_timestamp = time.time()

        self.sessions.append({
            "timestamp": time.time(),
            "duration": duration_sec,
            "earnings": earnings,
            "type": "Manual"
        })
        self.save_data()
        self.lbl_session_status.config(text=f"Manually logged: +{self.format_currency(earnings)}", fg="#64748b")

    # --- CORE LOGIC ---

    def calculate_economics(self):
        now = time.time()
        time_delta = now - self.last_calc_time
        self.last_calc_time = now

        # 1. Beregn Lønn
        if self.is_working:
            wage_per_sec = self.settings['hourly_wage'] / 3600.0
            earned = wage_per_sec * time_delta
            self.balance += earned
            self.last_work_timestamp = now # Holder yield aktiv

        # 2. Bestem Rentenivå
        time_since_work = now - (self.last_work_timestamp if self.last_work_timestamp else 0)
        is_yield_eligible = self.last_work_timestamp is not None and time_since_work < YIELD_CUTOFF_SECONDS
        
        current_apy = 0.0
        status_text = "Yield: Inactive"
        status_color = "#ef4444"

        if self.settings['use_plus_yield'] and self.is_working:
            # Plussrente er aktiv
            current_apy = self.settings['plus_apy']
            status_text = f"⚡ PLUS YIELD ({current_apy*100:.0f}%)"
            status_color = "#8b5cf6" # Purple
        elif is_yield_eligible:
            # Grunnrente er aktiv
            current_apy = self.settings['base_apy']
            expires_in_hours = (YIELD_CUTOFF_SECONDS - time_since_work) / 3600
            status_text = f"Base Yield ({current_apy*100:.0f}%) - {expires_in_hours:.1f}h left"
            status_color = "#10b981" # Green
        else:
            status_text = "Yield Inactive (Start working!)"

        # 3. Beregn Rente
        if current_apy > 0 and self.balance > 0:
            seconds_in_year = 365 * 24 * 60 * 60
            portion_of_year = time_delta / seconds_in_year
            multiplier = math.pow(1 + current_apy, portion_of_year)
            
            new_balance = self.balance * multiplier
            interest = new_balance - self.balance
            
            self.balance = new_balance
            self.total_yield += interest

        # UI Oppdatering
        self.lbl_balance.config(text=self.format_currency(self.balance))
        self.lbl_yield_status.config(text=status_text, fg=status_color)
        
        # Oppdater session timer hvis aktiv
        if self.is_working and self.current_session_start:
            elapsed = now - self.current_session_start
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            s = int(elapsed % 60)
            self.lbl_session_status.config(text=f"⏱ {h:02}:{m:02}:{s:02}", fg="#0f172a")

    def update_loop(self):
        self.calculate_economics()
        self.root.after(UPDATE_INTERVAL_MS, self.update_loop)

    # --- POPUP WINDOWS ---

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("300x400")
        win.configure(bg="#f8fafc")

        tk.Label(win, text="Hourly Wage (NOK)", bg="#f8fafc", font=("Helvetica", 9, "bold")).pack(pady=(15,5))
        wage_var = tk.DoubleVar(value=self.settings['hourly_wage'])
        tk.Entry(win, textvariable=wage_var).pack()

        tk.Label(win, text="Base APY (decimal, 0.25 = 25%)", bg="#f8fafc", font=("Helvetica", 9, "bold")).pack(pady=(15,5))
        base_apy_var = tk.DoubleVar(value=self.settings['base_apy'])
        tk.Entry(win, textvariable=base_apy_var).pack()

        tk.Label(win, text="Plus APY (decimal, 1.0 = 100%)", bg="#f8fafc", font=("Helvetica", 9, "bold")).pack(pady=(15,5))
        plus_apy_var = tk.DoubleVar(value=self.settings['plus_apy'])
        tk.Entry(win, textvariable=plus_apy_var).pack()

        tk.Label(win, text="Features", bg="#f8fafc", font=("Helvetica", 9, "bold")).pack(pady=(15,5))
        use_plus_var = tk.BooleanVar(value=self.settings['use_plus_yield'])
        tk.Checkbutton(win, text="Enable Plus Yield (Bonus when working)", variable=use_plus_var, bg="#f8fafc").pack()

        def save_settings():
            self.settings['hourly_wage'] = wage_var.get()
            self.settings['base_apy'] = base_apy_var.get()
            self.settings['plus_apy'] = plus_apy_var.get()
            self.settings['use_plus_yield'] = use_plus_var.get()
            self.save_data()
            self.lbl_info_wage.config(text=f"Wage: {self.settings['hourly_wage']} kr/h")
            win.destroy()

        tk.Button(win, text="Save & Close", command=save_settings, bg="#10b981", fg="white", font=("Helvetica", 10, "bold"), pady=5).pack(pady=20, fill="x", padx=20)

    def open_history(self):
        win = tk.Toplevel(self.root)
        win.title("History & Log")
        win.geometry("400x500")
        win.configure(bg="#f8fafc")

        # Manuell loggføring seksjon
        log_frame = tk.LabelFrame(win, text="Manual Entry", bg="#f8fafc", padx=10, pady=10)
        log_frame.pack(fill="x", padx=10, pady=10)
        
        f_in = tk.Frame(log_frame, bg="#f8fafc")
        f_in.pack()
        tk.Label(f_in, text="Hours:", bg="#f8fafc").pack(side="left")
        e_h = tk.Entry(f_in, width=5)
        e_h.pack(side="left", padx=5)
        tk.Label(f_in, text="Mins:", bg="#f8fafc").pack(side="left")
        e_m = tk.Entry(f_in, width=5)
        e_m.pack(side="left", padx=5)
        
        def do_log():
            self.manual_log(e_h.get(), e_m.get())
            refresh_list()
            e_h.delete(0, 'end')
            e_m.delete(0, 'end')

        tk.Button(log_frame, text="Add Past Session", command=do_log, bg="#3b82f6", fg="white").pack(pady=5)

        # Liste over sesjoner
        tk.Label(win, text="Recent Sessions", bg="#f8fafc", font=("Helvetica", 10, "bold")).pack(pady=5)
        
        list_frame = tk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        lb = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Courier", 9))
        lb.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=lb.yview)

        def refresh_list():
            lb.delete(0, tk.END)
            # Sorter nyeste først
            for s in reversed(self.sessions):
                date_str = datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d %H:%M")
                dur_m = int(s["duration"] // 60)
                earn_str = f"{s['earnings']:.2f} kr"
                type_str = s.get("type", "Session")
                lb.insert(tk.END, f"{date_str} | {type_str:7} | {dur_m:3}m | {earn_str}")

        refresh_list()


    # --- PERSISTENCE ---

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 0.0)
                    self.total_yield = data.get("total_yield", 0.0)
                    self.last_work_timestamp = data.get("last_work_timestamp")
                    self.sessions = data.get("sessions", [])
                    
                    # Merge saved settings with defaults to handle new keys
                    saved_settings = data.get("settings", {})
                    for k, v in saved_settings.items():
                        self.settings[k] = v
            except Exception as e:
                print(f"Error loading: {e}")

    def save_data(self):
        data = {
            "balance": self.balance,
            "total_yield": self.total_yield,
            "last_work_timestamp": self.last_work_timestamp,
            "sessions": self.sessions,
            "settings": self.settings
        }
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyBankApp(root)
    root.mainloop()
