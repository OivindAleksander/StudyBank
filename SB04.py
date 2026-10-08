import tkinter as tk
from tkinter import messagebox, font, ttk, simpledialog
import time
import json
import os
import math
import uuid  # Ny import for unike IDer på sparemål
from datetime import datetime, timedelta

# Prøv å importere matplotlib for grafer
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# --- STANDARD KONFIGURASJON ---
DEFAULT_SETTINGS = {
    "hourly_wage": 100.0,
    "base_apy": 0.25,      # 25%
    "plus_apy": 1.00,      # 100%
    "use_plus_yield": False
}

YIELD_CUTOFF_SECONDS = 24 * 60 * 60  # 24 timer
DATA_FILE = "studybank_data.json"
UPDATE_INTERVAL_MS = 100

class StudyBankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StudyBank Pro")
        self.root.geometry("450x700")
        self.root.configure(bg="#f0f2f5")

        # -- STATE --
        self.balance = 0.0      # "Liquid" cash in wallet
        self.total_yield = 0.0
        self.is_working = False
        
        self.current_session_start = None
        self.last_work_timestamp = None
        self.last_calc_time = time.time()
        
        self.sessions = []
        self.goals = []         # Liste med sparemål
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
        
        # Knapper i header (History, Goals, Settings)
        btn_frame_header = tk.Frame(header_frame, bg="#1e293b")
        btn_frame_header.pack(fill="x", padx=10, pady=5)
        
        btn_history = tk.Button(header_frame, text="📜 History", command=self.open_history, 
                                bg="#334155", fg="white", relief="flat", font=("Helvetica", 8))
        btn_history.place(relx=0.05, rely=0.5, anchor="w")

        # NY: Goals-knapp i midten (eller ved siden av)
        btn_goals = tk.Button(header_frame, text="🎯 Goals", command=self.open_goals,
                              bg="#334155", fg="white", relief="flat", font=("Helvetica", 8))
        btn_goals.place(relx=0.5, rely=0.5, anchor="center")

        btn_settings = tk.Button(header_frame, text="⚙ Settings", command=self.open_settings, 
                                 bg="#334155", fg="white", relief="flat", font=("Helvetica", 8))
        btn_settings.place(relx=0.95, rely=0.5, anchor="e")

        # Balance Card
        self.balance_frame = tk.Frame(self.root, bg="white", padx=20, pady=20, relief="flat")
        self.balance_frame.pack(pady=20, padx=20, fill="x")
        
        tk.Label(self.balance_frame, text="Total Net Worth", bg="white", fg="#64748b", font=("Helvetica", 10)).pack()
        self.lbl_net_worth = tk.Label(self.balance_frame, text="kr 0,00", bg="white", fg="#0f172a", font=balance_font)
        self.lbl_net_worth.pack(pady=5)
        
        # Breakdown Label (Wallet vs Goals)
        self.lbl_breakdown = tk.Label(self.balance_frame, text="Wallet: 0 | Goals: 0", bg="white", fg="#94a3b8", font=("Helvetica", 8))
        self.lbl_breakdown.pack()

        # Yield Status
        self.lbl_yield_status = tk.Label(self.balance_frame, text="Yield: Inactive", bg="white", fg="#ef4444", font=("Helvetica", 9, "bold"))
        self.lbl_yield_status.pack(pady=(10,0))

        # Info Grid
        info_frame = tk.Frame(self.root, bg="#f0f2f5")
        info_frame.pack(pady=5)
        self.lbl_info_wage = tk.Label(info_frame, text=f"Wage: {self.settings['hourly_wage']} kr/h", bg="#f0f2f5", fg="#64748b", font=("Helvetica", 8))
        self.lbl_info_wage.pack(side="left", padx=10)

        # Session Status
        self.lbl_session_status = tk.Label(self.root, text="Ready to work?", bg="#f0f2f5", fg="#64748b", font=self.status_font)
        self.lbl_session_status.pack(pady=20)

        # Main Buttons
        btn_frame = tk.Frame(self.root, bg="#f0f2f5")
        btn_frame.pack(pady=10)

        self.btn_start = tk.Button(btn_frame, text="START SESSION", command=self.start_session, 
                                   bg="#10b981", fg="white", font=("Helvetica", 12, "bold"), 
                                   width=15, height=2, relief="flat", activebackground="#059669")
        self.btn_start.pack(pady=5)

        self.btn_stop = tk.Button(btn_frame, text="STOP SESSION", command=self.stop_session, 
                                  bg="#ef4444", fg="white", font=("Helvetica", 12, "bold"), 
                                  width=15, height=2, relief="flat", activebackground="#dc2626")

        # Stats Button
        self.btn_stats = tk.Button(self.root, text="📊 View Statistics", command=self.open_stats,
                                  bg="#3b82f6", fg="white", font=("Helvetica", 10, "bold"),
                                  relief="flat", pady=8, width=20)
        self.btn_stats.pack(pady=20, side="bottom")

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
        
        wage_per_sec = self.settings['hourly_wage'] / 3600.0
        earnings = duration * wage_per_sec
        
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

        # Beregn verdier
        total_in_goals = sum(g['current'] for g in self.goals)
        net_worth = self.balance + total_in_goals

        # 1. Beregn Lønn
        if self.is_working:
            wage_per_sec = self.settings['hourly_wage'] / 3600.0
            earned = wage_per_sec * time_delta
            self.balance += earned
            # Oppdater net worth umiddelbart
            net_worth = self.balance + total_in_goals
            self.last_work_timestamp = now 

        # 2. Bestem Rentenivå
        time_since_work = now - (self.last_work_timestamp if self.last_work_timestamp else 0)
        is_yield_eligible = self.last_work_timestamp is not None and time_since_work < YIELD_CUTOFF_SECONDS
        
        current_apy = 0.0
        status_text = "Yield: Inactive"
        status_color = "#ef4444"

        if self.settings['use_plus_yield'] and self.is_working:
            current_apy = self.settings['plus_apy']
            status_text = f"⚡ PLUS YIELD ({current_apy*100:.0f}%)"
            status_color = "#8b5cf6" 
        elif is_yield_eligible:
            current_apy = self.settings['base_apy']
            expires_in_hours = (YIELD_CUTOFF_SECONDS - time_since_work) / 3600
            status_text = f"Base Yield ({current_apy*100:.0f}%) - {expires_in_hours:.1f}h left"
            status_color = "#10b981" 
        else:
            status_text = "Yield Inactive (Start working!)"

        # 3. Beregn Rente (På hele Net Worth!)
        if current_apy > 0 and net_worth > 0:
            seconds_in_year = 365 * 24 * 60 * 60
            portion_of_year = time_delta / seconds_in_year
            multiplier = math.pow(1 + current_apy, portion_of_year)
            
            # Beregn ny totalformue
            new_net_worth = net_worth * multiplier
            interest = new_net_worth - net_worth
            
            # Utbetal renter til Wallet (Liquid Cash)
            self.balance += interest
            self.total_yield += interest

            # Oppdater net worth etter renteutbetaling for visning
            net_worth = self.balance + total_in_goals

        # UI Oppdatering
        self.lbl_net_worth.config(text=self.format_currency(net_worth))
        self.lbl_breakdown.config(text=f"Wallet: {self.format_currency(self.balance)} | Goals: {self.format_currency(total_in_goals)}")
        self.lbl_yield_status.config(text=status_text, fg=status_color)
        
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
        win.geometry("300x450")
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
        
        list_frame = tk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        lb = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Courier", 9))
        lb.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=lb.yview)

        def refresh_list():
            lb.delete(0, tk.END)
            for s in reversed(self.sessions):
                date_str = datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d %H:%M")
                dur_m = int(s["duration"] // 60)
                earn_str = f"{s['earnings']:.2f} kr"
                type_str = s.get("type", "Session")
                lb.insert(tk.END, f"{date_str} | {type_str:7} | {dur_m:3}m | {earn_str}")

        refresh_list()

    def open_goals(self):
        win = tk.Toplevel(self.root)
        win.title("Savings Goals")
        win.geometry("400x600")
        win.configure(bg="#f8fafc")

        # Scrollable area for goals
        canvas = tk.Canvas(win, bg="#f8fafc", highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8fafc")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=380) # Width fix
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        # Function to refresh goal list
        def refresh_goals():
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            for goal in self.goals:
                draw_goal_card(goal)

            # "New Goal" Form at bottom of scrollable area
            draw_new_goal_form()

        def draw_goal_card(goal):
            card = tk.Frame(scrollable_frame, bg="white", padx=10, pady=10, relief="solid", bd=1)
            card.pack(fill="x", pady=5, padx=5)

            # Header
            header = tk.Frame(card, bg="white")
            header.pack(fill="x")
            tk.Label(header, text=goal['name'], bg="white", font=("Helvetica", 10, "bold")).pack(side="left")
            pct = min(100, (goal['current'] / goal['target'] * 100)) if goal['target'] > 0 else 0
            tk.Label(header, text=f"{pct:.1f}%", bg="white", fg="#64748b").pack(side="right")

            # Progress Bar
            pb = ttk.Progressbar(card, orient="horizontal", length=100, mode="determinate")
            pb['value'] = pct
            pb.pack(fill="x", pady=5)

            # Amounts
            tk.Label(card, text=f"{self.format_currency(goal['current'])} / {self.format_currency(goal['target'])}", bg="white", fg="#64748b", font=("Courier", 9)).pack(pady=2)

            # Buttons
            btn_box = tk.Frame(card, bg="white")
            btn_box.pack(fill="x", pady=5)

            def deposit(g_id=goal['id']):
                amt = simpledialog.askfloat("Deposit", "Amount to move from Wallet to Goal:", parent=win)
                if amt and amt > 0:
                    if amt <= self.balance:
                        self.balance -= amt
                        for g in self.goals:
                            if g['id'] == g_id: g['current'] += amt
                        self.save_data()
                        refresh_goals()
                    else:
                        messagebox.showerror("Error", "Insufficient funds in Wallet.")

            def withdraw(g_id=goal['id']):
                amt = simpledialog.askfloat("Withdraw", "Amount to move from Goal to Wallet:", parent=win)
                if amt and amt > 0:
                    for g in self.goals:
                        if g['id'] == g_id:
                            if amt <= g['current']:
                                g['current'] -= amt
                                self.balance += amt
                                self.save_data()
                                refresh_goals()
                            else:
                                messagebox.showerror("Error", "Insufficient funds in Goal.")
            
            def buy(g_id=goal['id'], g_name=goal['name']):
                if messagebox.askyesno("Confirm Purchase", f"Buy '{g_name}'? The money will be spent and gone."):
                    self.goals = [g for g in self.goals if g['id'] != g_id]
                    self.save_data()
                    refresh_goals()
                    messagebox.showinfo("Success", f"Congratulations on your new {g_name}!")

            tk.Button(btn_box, text="+ Dep", command=deposit, bg="#dbeafe", fg="#1e40af", width=6, relief="flat").pack(side="left", padx=2)
            tk.Button(btn_box, text="- Wdr", command=withdraw, bg="#f1f5f9", fg="#475569", width=6, relief="flat").pack(side="left", padx=2)
            tk.Button(btn_box, text="🛒 BUY", command=buy, bg="#dcfce7", fg="#166534", width=6, relief="flat").pack(side="right", padx=2)

        def draw_new_goal_form():
            f = tk.LabelFrame(scrollable_frame, text="Create New Goal", bg="#f8fafc", padx=10, pady=10)
            f.pack(fill="x", pady=20, padx=5)
            
            tk.Label(f, text="Name:", bg="#f8fafc").pack(anchor="w")
            e_name = tk.Entry(f)
            e_name.pack(fill="x", pady=(0, 5))
            
            tk.Label(f, text="Target Amount:", bg="#f8fafc").pack(anchor="w")
            e_amount = tk.Entry(f)
            e_amount.pack(fill="x", pady=(0, 10))
            
            def create():
                name = e_name.get()
                try:
                    target = float(e_amount.get())
                except ValueError:
                    return
                
                if name and target > 0:
                    new_goal = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "target": target,
                        "current": 0.0
                    }
                    self.goals.append(new_goal)
                    self.save_data()
                    refresh_goals()

            tk.Button(f, text="Create Goal", command=create, bg="#1e293b", fg="white").pack(fill="x")

        refresh_goals()

    def open_stats(self):
        if not HAS_MATPLOTLIB:
            messagebox.showinfo("Missing Library", "To view charts, you need to install matplotlib.\nRun: pip install matplotlib")
            return

        win = tk.Toplevel(self.root)
        win.title("Statistics Dashboard")
        win.geometry("800x800")
        win.configure(bg="#f8fafc")

        # --- DATA PROCESSING ---
        total_time_sec = sum(s['duration'] for s in self.sessions)
        total_wage_earnings = sum(s['earnings'] for s in self.sessions)
        avg_session = total_time_sec / len(self.sessions) if self.sessions else 0
        
        # Siste 7 dager
        days = []
        hours_per_day = []
        today = datetime.now().date()
        
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_str = d.strftime("%a") # Mon, Tue...
            days.append(day_str)
            
            # Sum timer for denne dagen
            daily_sec = sum(s['duration'] for s in self.sessions 
                            if datetime.fromtimestamp(s['timestamp']).date() == d)
            hours_per_day.append(daily_sec / 3600)

        # --- 1. KPI SECTION ---
        kpi_frame = tk.Frame(win, bg="#f8fafc")
        kpi_frame.pack(fill="x", pady=20, padx=20)
        
        def create_kpi(parent, title, value, color="#1e293b"):
            f = tk.Frame(parent, bg="white", padx=15, pady=15, relief="flat", bd=1)
            f.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(f, text=title, bg="white", fg="#64748b", font=("Helvetica", 9)).pack()
            tk.Label(f, text=value, bg="white", fg=color, font=("Helvetica", 14, "bold")).pack()

        create_kpi(kpi_frame, "Total Hours", f"{total_time_sec/3600:.1f} h")
        create_kpi(kpi_frame, "Avg Session", f"{avg_session/60:.0f} min")
        create_kpi(kpi_frame, "Labor Income", f"{total_wage_earnings:.0f} kr", "#3b82f6")
        create_kpi(kpi_frame, "Passive Yield", f"{self.total_yield:.0f} kr", "#10b981")

        # --- 2. BAR CHART (Weekly Effort) ---
        fig1 = Figure(figsize=(6, 3), dpi=100)
        ax1 = fig1.add_subplot(111)
        ax1.bar(days, hours_per_day, color="#3b82f6", alpha=0.7)
        ax1.set_title("Weekly Effort (Hours)", fontsize=10)
        ax1.set_ylabel("Hours")
        ax1.grid(axis='y', linestyle='--', alpha=0.5)
        # Style tweaks
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        fig1.tight_layout()

        canvas1 = FigureCanvasTkAgg(fig1, master=win)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        # --- 3. PIE CHART (Income Sources) ---
        fig2 = Figure(figsize=(6, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        
        labels = ['Wage (Labor)', 'Yield (Passive)']
        sizes = [total_wage_earnings, self.total_yield]
        colors = ['#93c5fd', '#86efac'] # Light blue, Light green
        
        # Unngå å plotte hvis begge er 0
        if sum(sizes) > 0:
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            ax2.set_title("Income Distribution", fontsize=10)
        else:
            ax2.text(0.5, 0.5, "No income data yet", ha='center')

        canvas2 = FigureCanvasTkAgg(fig2, master=win)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)


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
                    self.goals = data.get("goals", []) # Load goals
                    
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
            "goals": self.goals, # Save goals
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