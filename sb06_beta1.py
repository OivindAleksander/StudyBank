"""StudyBank sb06_beta1: statistics dashboard on top of SB05y."""
import csv
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import SB05y as legacy
from studybank_stats import summarize

BG = '#f3f5f9'
INK = '#17243b'
MUTED = '#64748b'
BLUE = '#5264e8'
TEAL = '#159b86'


class StudyBankApp(legacy.StudyBankApp):
    def __init__(self, root):
        self.stats_window = None
        super().__init__(root)
        root.title('StudyBank · sb06_beta1')
        self.btn_stats.configure(text='Statistikk  ↗')

    def open_stats(self):
        if self.stats_window is not None and self.stats_window.winfo_exists():
            self.stats_window.lift()
            self.stats_window.focus_force()
            return
        self.stats_window = StatisticsWindow(self)


class StatisticsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('StudyBank · Statistikk · sb06_beta1')
        self.geometry('1120x900')
        self.minsize(760, 640)
        self.configure(bg=BG)
        self.period = tk.StringVar(value='30 dager')
        self.compare = tk.BooleanVar(value=True)
        self.chart = None
        self.figure = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda event: self.close())
        self.bind('<F5>', lambda event: self.refresh())

        header = tk.Frame(self, bg=INK, padx=28, pady=18)
        header.pack(fill='x')
        self.label(header, 'STUDYBANK  /  INNSIKT', 11, '#b9c5de', INK).pack(side='left')
        self.label(header, 'sb06_beta1', 10, '#b9c5de', INK).pack(side='right')
        heading = tk.Frame(self, bg=BG, padx=28, pady=18)
        heading.pack(fill='x')
        self.label(heading, 'Små økter. Stor fremgang.', 25, INK, BG, True).pack(anchor='w')
        self.label(heading, 'Se hva innsatsen din blir til, én dag av gangen.', 11, MUTED, BG).pack(anchor='w', pady=(6, 0))

        toolbar = tk.Frame(self, bg=BG, padx=28)
        toolbar.pack(fill='x', pady=(0, 16))
        period = ttk.Combobox(toolbar, textvariable=self.period, values=['7 dager', '30 dager', '90 dager'], state='readonly', width=12)
        period.pack(side='left', padx=(0, 12))
        period.bind('<<ComboboxSelected>>', lambda event: self.refresh())
        tk.Checkbutton(toolbar, text='Sammenlign med forrige periode', variable=self.compare,
                       command=self.refresh, bg=BG, fg=MUTED, activebackground=BG).pack(side='left')
        self.button(toolbar, 'Eksporter CSV', self.export).pack(side='right')
        self.button(toolbar, 'Oppdater · F5', self.refresh).pack(side='right', padx=8)

        # The entire dashboard scrolls, so charts and history remain accessible on small screens.
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill='both', expand=True)
        self.viewport = tk.Canvas(shell, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient='vertical', command=self.viewport.yview)
        scrollbar.pack(side='right', fill='y')
        self.viewport.pack(side='left', fill='both', expand=True)
        self.viewport.configure(yscrollcommand=scrollbar.set)
        self.body = tk.Frame(self.viewport, bg=BG, padx=28)
        body_id = self.viewport.create_window((0, 0), window=self.body, anchor='nw')
        self.viewport.bind('<Configure>', lambda e: self.viewport.itemconfigure(body_id, width=e.width))
        self.body.bind('<Configure>', lambda e: self.viewport.configure(scrollregion=self.viewport.bbox('all')))
        self.bind('<MouseWheel>', self.scroll)
        self.bind('<Button-4>', lambda e: self.viewport.yview_scroll(-3, 'units'))
        self.bind('<Button-5>', lambda e: self.viewport.yview_scroll(3, 'units'))
        self.refresh()

    def scroll(self, event):
        self.viewport.yview_scroll(-1 if event.delta > 0 else 1, 'units')

    @staticmethod
    def label(parent, text, size=11, fg=INK, bg='white', bold=False):
        return tk.Label(parent, text=text, bg=bg, fg=fg,
                        font=('Helvetica', size, 'bold' if bold else 'normal'), anchor='w')

    @staticmethod
    def button(parent, text, command):
        return tk.Button(parent, text=text, command=command, bg='white', fg=INK,
                         activebackground='#e5e9fa', relief='flat', padx=12, pady=7, cursor='hand2')

    def refresh(self):
        self.report = summarize(self.app.sessions, int(self.period.get().split()[0]))
        if self.figure is not None:
            self.figure.clear()
        for child in self.body.winfo_children():
            child.destroy()
        self.chart = self.figure = None
        r = self.report
        dates = f"{r['dates'][0]:%d.%m.%Y} – {r['dates'][-1]:%d.%m.%Y}"
        self.label(self.body, dates + '  ·  Fullførte og manuelt registrerte økter', 10, MUTED, BG).pack(anchor='w', pady=(0, 12))
        cards = tk.Frame(self.body, bg=BG)
        cards.pack(fill='x')
        change = r['hours'] - r['previous_hours']
        comparison = f"{change:+.1f} t mot forrige periode"
        metrics = [
            ('STUDIETID', f"{r['hours']:.1f} t", comparison, BLUE),
            ('ARBEIDSINNTEKT', f"{r['earnings']:,.0f} kr", 'Fra registrerte økter', TEAL),
            ('FULLFØRTE ØKTER', str(len(r['sessions'])), f"Snitt {r['average_minutes']:.0f} min per økt", INK),
            ('AKTIVE DAGER', f"{r['active_days']} / {len(r['dates'])}", 'Dager med registrert studietid', INK),
        ]
        for i, (title, value, note, color) in enumerate(metrics):
            cards.columnconfigure(i, weight=1, uniform='cards')
            card = tk.Frame(cards, bg='white', padx=16, pady=18)
            card.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            self.label(card, title, 9, MUTED).pack(anchor='w')
            self.label(card, value, 23, color, bold=True).pack(anchor='w', pady=8)
            label = self.label(card, note, 9, MUTED)
            label.configure(wraplength=170)
            label.pack(anchor='w')
        if not r['sessions']:
            self.label(self.body, 'Ingen økter i perioden. Start en økt eller registrer tid fra History.', 11, MUTED, BG).pack(anchor='w', pady=(16, 0))
        if r['skipped']:
            self.label(self.body, f"{r['skipped']} ugyldige registreringer er utelatt.", 10, '#ad5c14', BG).pack(anchor='w', pady=(10, 0))
        if legacy.HAS_MATPLOTLIB:
            self.draw_charts()
        else:
            self.label(self.body, 'Diagrammer krever matplotlib: python -m pip install -r requirements.txt', 11, MUTED, BG).pack(pady=24)
        insight = tk.Frame(self.body, bg='#e6edf9', padx=18, pady=14)
        insight.pack(fill='x', pady=16)
        best = max(zip(r['daily_hours'], r['dates']))
        message = f"Beste dag i perioden: {best[1]:%d.%m} · {best[0]:.1f} timer" if r['active_days'] else 'Din neste økt er starten på en ny vane.'
        self.label(insight, message, 11, INK, '#e6edf9', True).pack(anchor='w')
        self.label(insight, f"Saldo nå: {self.app.balance:,.2f} kr  ·  Avkastning totalt: {self.app.total_yield:,.2f} kr", 10, MUTED, '#e6edf9').pack(anchor='w', pady=(6, 0))
        self.label(insight, 'Saldo og avkastning er totaltall og følger ikke periodefilteret.', 9, MUTED, '#e6edf9').pack(anchor='w', pady=(4, 0))
        self.draw_history()
        self.label(self.body, 'Økter føres på sluttdatoen i lokal tid. Pågående økt er ikke inkludert. Oppdater med F5.', 9, MUTED, BG).pack(anchor='w', pady=16)

    def draw_charts(self):
        r = self.report
        panel = tk.Frame(self.body, bg='white', padx=16, pady=16)
        panel.pack(fill='x', pady=(18, 0))
        self.label(panel, 'Innsatsen din over tid', 15, bold=True).pack(anchor='w')
        self.label(panel, 'Hold pekeren over linjene for detaljer. Forrige periode er forskjøvet for sammenligning.', 10, MUTED).pack(anchor='w', pady=(5, 8))
        self.figure = legacy.Figure(figsize=(10, 4.5), dpi=100, facecolor='white')
        axes = self.figure.subplots(1, 2)
        self.figure.subplots_adjust(left=.07, right=.97, bottom=.19, top=.86, wspace=.28)
        x = list(range(len(r['dates'])))
        cumulative = []
        total = 0
        for value in r['daily_earnings']:
            total += value
            cumulative.append(total)
        self.plot_series = []
        for ax, current, previous, title, unit, color in [
            (axes[0], r['daily_hours'], r['previous_daily_hours'], 'Daglig studietid', 'timer', BLUE),
            (axes[1], cumulative, r['previous_cumulative_earnings'], 'Samlet arbeidsinntekt i perioden', 'kr', TEAL),
        ]:
            ax.set_title(title, loc='left', fontsize=11, color=INK, pad=18)
            ax.plot(x, current, color=color, linewidth=2.4, label='Valgt periode')
            ax.fill_between(x, current, color=color, alpha=.08)
            if self.compare.get():
                ax.plot(x, previous, color='#8996ad', linewidth=1.5, linestyle='--', label='Forrige periode')
            ax.set_ylim(bottom=0, top=max(max(current), max(previous) if self.compare.get() else 0, 1) * 1.18)
            ticks = sorted(set([0, len(x)//4, len(x)//2, 3*len(x)//4, len(x)-1]))
            ax.set_xticks(ticks, [r['dates'][i].strftime('%d.%m') for i in ticks])
            ax.set_ylabel(unit, color=MUTED, fontsize=9)
            ax.tick_params(axis='both', labelsize=8, colors=MUTED, length=0, pad=8)
            ax.grid(axis='y', color='#edf0f5')
            ax.set_axisbelow(True)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.legend(loc='upper left', fontsize=8, frameon=False)
            annotation = ax.annotate('', xy=(0, 0), xytext=(8, 14), textcoords='offset points',
                                     bbox=dict(boxstyle='round,pad=.5', fc=INK, ec=INK), color='white', fontsize=9)
            annotation.set_visible(False)
            self.plot_series.append((ax, current, previous, unit, annotation))
        self.chart = legacy.FigureCanvasTkAgg(self.figure, master=panel)
        self.chart.get_tk_widget().configure(height=365)
        self.chart.get_tk_widget().pack(fill='x')
        self.chart.mpl_connect('motion_notify_event', self.hover)
        self.chart.draw()

    def hover(self, event):
        for ax, values, previous, unit, annotation in self.plot_series:
            visible = event.inaxes is ax and event.xdata is not None
            annotation.set_visible(visible)
            if visible:
                i = max(0, min(len(values)-1, round(event.xdata)))
                annotation.xy = (i, values[i])
                annotation.set_position((-8 if i > len(values)/2 else 8, 14))
                annotation.set_ha('right' if i > len(values)/2 else 'left')
                label = f"{self.report['dates'][i]:%d.%m}: {values[i]:.1f} {unit}"
                if self.compare.get():
                    label += f"\nForrige: {previous[i]:.1f} {unit}"
                annotation.set_text(label)
        self.chart.draw_idle()

    def draw_history(self):
        panel = tk.Frame(self.body, bg='white', padx=16, pady=16)
        panel.pack(fill='x')
        self.label(panel, 'Økthistorikk', 15, bold=True).pack(anchor='w', pady=(0, 12))
        frame = tk.Frame(panel, bg='white')
        frame.pack(fill='x')
        self.table = ttk.Treeview(frame, columns=('date', 'duration', 'earnings', 'type'), show='headings', height=6)
        for name, title, width in [('date', 'Dato og tidspunkt', 190), ('duration', 'Minutter', 120), ('earnings', 'Inntekt (kr)', 140), ('type', 'Registrering', 150)]:
            self.table.heading(name, text=title, command=lambda n=name: self.sort_history(n))
            self.table.column(name, width=width, anchor='w')
        bar = ttk.Scrollbar(frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=bar.set)
        self.table.pack(side='left', fill='x', expand=True)
        bar.pack(side='right', fill='y')
        self.sort_column, self.sort_reverse = 'date', True
        self.populate_history()

    def sort_history(self, column):
        self.sort_reverse = not self.sort_reverse if self.sort_column == column else False
        self.sort_column = column
        self.populate_history()

    def populate_history(self):
        self.table.delete(*self.table.get_children())
        key = {'date': 'timestamp', 'duration': 'duration', 'earnings': 'earnings', 'type': 'type'}[self.sort_column]
        for s in sorted(self.report['sessions'], key=lambda row: row[key], reverse=self.sort_reverse):
            self.table.insert('', 'end', values=(datetime.fromtimestamp(s['timestamp']).strftime('%d.%m.%Y %H:%M'),
                                                f"{s['duration']/60:.1f}", f"{s['earnings']:.2f}",
                                                'Manuell' if s['type'] == 'Manual' else 'Studieøkt'))

    def export(self):
        if not self.report['sessions']:
            messagebox.showinfo('Ingen økter', 'Ingen økter å eksportere i denne perioden.', parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title='Eksporter valgt periode', defaultextension='.csv',
                                          initialfile='sb06_beta1_statistikk.csv', filetypes=[('CSV', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(['Dato (lokal tid)', 'Varighet (min)', 'Arbeidsinntekt (kr)', 'Type'])
                for s in self.report['sessions']:
                    writer.writerow([datetime.fromtimestamp(s['timestamp']).isoformat(timespec='seconds'),
                                     f"{s['duration']/60:.2f}", f"{s['earnings']:.2f}",
                                     'Manuell' if s['type'] == 'Manual' else 'Studieøkt'])
            messagebox.showinfo('Eksportert', 'Øktene i valgt periode er eksportert.', parent=self)
        except OSError as error:
            messagebox.showerror('Kunne ikke eksportere', str(error), parent=self)

    def close(self):
        if self.figure is not None:
            self.figure.clear()
        self.destroy()
        self.app.stats_window = None


if __name__ == '__main__':
    # Keep existing data beside the application, independent of the launch directory.
    legacy.DATA_FILE = str(Path(__file__).resolve().with_name('studybank_data.json'))
    root = tk.Tk()
    app = StudyBankApp(root)
    root.mainloop()
