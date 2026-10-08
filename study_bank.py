import tkinter as tk
from tkinter import messagebox, font
import time
import json
import os
import math

# --- KONFIGURASJON ---
HOURLY_WAGE_NOK = 100.0
APY = 0.25  # 25% rente
YIELD_CUTOFF_SECONDS = 24 * 60 * 60  # 24 timer
DATA_FILE = "studybank_data.json"
UPDATE_INTERVAL_MS = 100  # Oppdateringsfrekvens for UI og kalkulasjoner

class StudyBankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StudyBank Python")
        self.root.geometry("400x500")
        self.root.configure(bg="#f0f2f5")

        # -- STATE --
        self.balance = 0.0
        self.is_working = False
        self.last_work_timestamp = None
        self.last_calc_time = time.time()
        
        # Last inn data hvis filen finnes
        self.load_data()

        # -- UI OPPSETT --
        self.setup_ui()
        
        # Start hovedløkken for økonomien
        self.update_loop()

    def setup_ui(self):
        # Fonter
        title_font = font.Font(family="Helvetica", size=12, weight="bold")
        balance_font = font.Font(family="Courier", size=30, weight="bold")
        status_font = font.Font(family="Helvetica", size=10)

        # Header
        header = tk.Label(self.root, text="STUDY BANK", bg="#1e293b", fg="white", font=title_font, pady=15)
        header.pack(fill="x")

        # Balance Card
        self.balance_frame = tk.Frame(self.root, bg="white", padx=20, pady=20, relief="flat")
        self.balance_frame.pack(pady=20, padx=20, fill="x")
        
        tk.Label(self.balance_frame, text="Total Net Worth", bg="white", fg="#64748b", font=("Helvetica", 10)).pack()
        self.lbl_balance = tk.Label(self.balance_frame, text="kr 0,00", bg="white", fg="#0f172a", font=balance_font)
        self.lbl_balance.pack(pady=5)

        # Yield Status
        self.lbl_yield_status = tk.Label(self.balance_frame, text="Yield: Inactive", bg="white", fg="#ef4444", font=("Helvetica", 9, "bold"))
        self.lbl_yield_status.pack()

        # Session Status
        self.lbl_session_status = tk.Label(self.root, text="Ready to work?", bg="#f0f2f5", fg="#64748b", font=status_font)
        self.lbl_session_status.pack(pady=10)

        # Knapper
        btn_frame = tk.Frame(self.root, bg="#f0f2f5")
        btn_frame.pack(pady=10)

        self.btn_start = tk.Button(btn_frame, text="START SESSION", command=self.start_session, 
                                   bg="#10b981", fg="white", font=("Helvetica", 12, "bold"), 
                                   width=15, height=2, relief="flat", activebackground="#059669")
        self.btn_start.pack(pady=5)

        self.btn_stop = tk.Button(btn_frame, text="STOP SESSION", command=self.stop_session, 
                                  bg="#ef4444", fg="white", font=("Helvetica", 12, "bold"), 
                                  width=15, height=2, relief="flat", activebackground="#dc2626")
        # Stop-knappen vises ikke før vi starter
        
    def format_currency(self, amount):
        return f"kr {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def start_session(self):
        self.is_working = True
        self.last_work_timestamp = time.time() # Aktiverer yield
        self.btn_start.pack_forget()
        self.btn_stop.pack(pady=5)
        self.lbl_session_status.config(text="🔥 Session Active - Earning Money!", fg="#10b981")
        self.save_data()

    def stop_session(self):
        self.is_working = False
        self.last_work_timestamp = time.time() # Oppdaterer timestamp slik at yield fortsetter i 24t
        self.btn_stop.pack_forget()
        self.btn_start.pack(pady=5)
        self.lbl_session_status.config(text="Session Stopped. Yield active for 24h.", fg="#64748b")
        self.save_data()

    def calculate_economics(self):
        now = time.time()
        time_delta = now - self.last_calc_time
        self.last_calc_time = now

        # 1. Beregn Lønn (hvis man jobber)
        if self.is_working:
            # Lønn per sekund = Timelønn / 3600
            wage_per_sec = HOURLY_WAGE_NOK / 3600.0
            earned = wage_per_sec * time_delta
            self.balance += earned
            # Oppdater timestamp kontinuerlig mens man jobber
            self.last_work_timestamp = now

        # 2. Beregn Rente (Yield)
        # Sjekk om yield er aktiv (innenfor 24 timer siden sist jobb)
        time_since_work = now - (self.last_work_timestamp if self.last_work_timestamp else 0)
        is_yield_active = self.last_work_timestamp is not None and time_since_work < YIELD_CUTOFF_SECONDS

        if is_yield_active and self.balance > 0:
            # Renteformel for kontinuerlig tid: A = P * e^(rt) eller diskret steg.
            # Vi bruker (1 + r)^t formel tilpasset sekunder.
            seconds_in_year = 365 * 24 * 60 * 60
            portion_of_year = time_delta / seconds_in_year
            
            multiplier = math.pow(1 + APY, portion_of_year)
            new_balance = self.balance * multiplier
            self.balance = new_balance

            # UI Oppdatering for Yield
            expires_in_hours = (YIELD_CUTOFF_SECONDS - time_since_work) / 3600
            self.lbl_yield_status.config(text=f"Yield Active ({APY*100}% APY) - Expires in {expires_in_hours:.1f}h", fg="#10b981")
        else:
            self.lbl_yield_status.config(text="Yield Inactive (No study in 24h)", fg="#ef4444")

        # Oppdater hovedsaldo i UI
        self.lbl_balance.config(text=self.format_currency(self.balance))

    def update_loop(self):
        self.calculate_economics()
        
        # Lagre data jevnlig (f.eks. hvert minutt) for sikkerhet, 
        # men her gjør vi det enkelt ved start/stop. 
        # Du kan legge inn en counter her hvis du vil lagre oftere.
        
        # Kjør loopen igjen om X millisekunder
        self.root.after(UPDATE_INTERVAL_MS, self.update_loop)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 0.0)
                    self.last_work_timestamp = data.get("last_work_timestamp")
            except Exception as e:
                print(f"Error loading data: {e}")

    def save_data(self):
        data = {
            "balance": self.balance,
            "last_work_timestamp": self.last_work_timestamp
        }
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving data: {e}")

# --- HOVEDPROGRAM ---
if __name__ == "__main__":
    root = tk.Tk()
    app = StudyBankApp(root)
    root.mainloop()
