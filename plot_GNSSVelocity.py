import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.widgets import Button
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk

# =========================================================================
# PARACADUTE WINDOWS & ESEGUIBILE (.EXE) DI SICUREZZA
# =========================================================================
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    percorso_rasterio = os.path.join(base_dir, "rasterio", "proj_data")
    percorso_pyproj   = os.path.join(base_dir, "pyproj", "proj_dir", "share", "proj")
else:
    percorso_rasterio = r"C:\Users\cecer\AppData\Roaming\Python\Python313\site-packages\rasterio\proj_data"
    percorso_pyproj   = r"C:\Users\cecer\AppData\Roaming\Python\Python313\site-packages\pyproj\proj_dir\share\proj"

if os.path.exists(percorso_rasterio):
    os.environ['PROJ_DATA'] = percorso_rasterio
    os.environ['PROJ_LIB']  = percorso_rasterio
elif os.path.exists(percorso_pyproj):
    os.environ['PROJ_DATA'] = percorso_pyproj
    os.environ['PROJ_LIB']  = percorso_pyproj
# =========================================================================

try:
    import contextily as ctx
except ImportError as e:
    print(f"\n[ERRORE] Problema con contextily o dipendenze: {e}\n")
    input("Premi INVIO per uscire...")
    sys.exit()


# =========================================================================
# SELEZIONE FILE TRAMITE ESPLORA RISORSE
# =========================================================================
def seleziona_file_input():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    percorso = filedialog.askopenfilename(
        title="Seleziona il file di velocità GNSS",
        filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
    )
    root.destroy()
    return percorso if percorso else None


# =========================================================================
# FINESTRA AIUTO
# =========================================================================
TESTO_AIUTO = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          GUIDA ALL'USO – Visualizzatore Velocità GNSS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODALITÀ 1 – RIFERIMENTO SINGOLA STAZIONE
──────────────────────────────────────────
  • Click sinistro su un sito  →  Riferimento su singola stazione.

MODALITÀ 2 – RIFERIMENTO SU AREA (MULTI-STAZIONE)
───────────────────────────────────────────────────
  • [M]  →  entra / esci dalla modalità multi-stazione (inner constraint).
  • Ctrl+Click su più siti per aggiungerli al gruppo.

MODALITÀ 3 – RIFERIMENTO EURASIA (ITRF2014)
───────────────────────────────────────────────────
  • [E]  →  Sottrae "al volo" il polo di rotazione della placca Eurasiatica, 
            utilizzando il modello ITRF2014 PMM (Altamimi et al., 2017).

MODALITÀ 4 – RIFERIMENTO POLO DI ADRIA (APPROCCIO RIGOROSO)
───────────────────────────────────────────────────
  • [A]  →  Applica un filtraggio cinematico a due stadi:
             1. Sottrae il frame assoluto ITRF2014 -> Eurasia
             2. Sottrae il polo relativo Eurasia -> Adria (D'Agostino et al., 2008)
            La posizione del polo (45.790°N, 7.780°E) viene visualizzata
            con una stella magenta sulla mappa.

NAVIGAZIONE MAPPA
─────────────────
  Tasti:
    [+] o [=]  →  aumenta la scala delle frecce
    [-]        →  diminuisce la scala delle frecce
    [T]        →  apre la tabella con i valori correnti
    [M]        →  attiva Modalità Multi-stazione
    [E]        →  attiva Placca Eurasia (ITRF2014)
    [A]        →  attiva Microplacca Adria (Rigoroso ITRF2014)
    [S]        →  mostra / nascondi le sigle delle stazioni
    [R]        →  resetta (torna ai vettori ITRF assoluti)
    [?]        →  mostra questa guida
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def mostra_aiuto():
    win = tk.Toplevel()
    win.title("Guida – Visualizzatore Velocità GNSS")
    win.resizable(True, True)

    frame = tk.Frame(win)
    frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    txt = tk.Text(frame, wrap=tk.WORD, font=("Courier New", 10),
                  bg="#f8f8f8", relief=tk.FLAT, padx=10, pady=10)
    sb  = ttk.Scrollbar(frame, command=txt.yview)
    txt.configure(yscrollcommand=sb.set)

    txt.grid(row=0, column=0, sticky="nsew")
    sb.grid (row=0, column=1, sticky="ns")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    txt.insert(tk.END, TESTO_AIUTO)
    txt.configure(state=tk.DISABLED)

    tk.Button(win, text="Chiudi", command=win.destroy,
              bg="#c0c0c0", font=("Arial", 10)).pack(pady=(0, 8))


# =========================================================================
# FINESTRA TABELLA VELOCITÀ
# =========================================================================
class FinestraTabella:
    def __init__(self, nomi, lon, lat, de, dn, du, descrizione_riferimento, percorso_input):
        self.nomi = nomi
        self.lon = lon
        self.lat = lat
        self.de = de
        self.dn = dn
        self.du = du
        self.descrizione_riferimento = descrizione_riferimento
        self.percorso_input = percorso_input

        self.root = tk.Toplevel()
        self.root.title("Tabella Velocità GNSS")
        self.root.resizable(True, True)
        self._costruisci_ui()

    def _costruisci_ui(self):
        stato = self.descrizione_riferimento or "Velocità assolute"
        tk.Label(self.root, text=stato, font=("Arial", 10, "bold"),
                 fg="navy", wraplength=560).pack(pady=(8, 2), padx=10)

        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        cols = ("Stazione", "Lon (°)", "Lat (°)", "dE (mm/yr)", "dN (mm/yr)", "dU (mm/yr)")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)

        for col, larg in zip(cols, [110, 90, 90, 90, 90, 90]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=larg, anchor="center")

        sy = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("pari",    background="#f0f4ff")
        self.tree.tag_configure("dispari", background="#ffffff")

        for i, nome in enumerate(self.nomi):
            tag = "pari" if i % 2 == 0 else "dispari"
            self.tree.insert("", tk.END, values=(
                nome,
                f"{self.lon[i]:.5f}", f"{self.lat[i]:.5f}",
                f"{self.de[i]:.4f}",  f"{self.dn[i]:.4f}",  f"{self.du[i]:.4f}",
            ), tags=(tag,))

        tk.Button(
            self.root, text="💾  Esporta velocità in file .txt",
            command=self._esporta, bg="#2060a0", fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT, padx=10, pady=6
        ).pack(pady=(4, 10))

    def _esporta(self):
        cartella_default = os.path.dirname(self.percorso_input)
        tag_nome = (self.descrizione_riferimento or "assolute") \
                       .replace(" ", "_").replace(":", "")[:40]
        nome_default = f"velocita_{tag_nome}.txt"

        root_tmp = tk.Tk(); root_tmp.withdraw()
        root_tmp.attributes('-topmost', True)
        percorso_out = filedialog.asksaveasfilename(
            title="Salva velocità GNSS",
            initialdir=cartella_default, initialfile=nome_default,
            defaultextension=".txt",
            filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
        )
        root_tmp.destroy()
        if not percorso_out:
            return

        try:
            with open(percorso_out, 'w') as f:
                f.write(f"# {self.descrizione_riferimento or 'Velocità GNSS assolute'}\n")
                f.write("# Formato: Lon(°)  Lat(°)  dE(mm/yr)  dN(mm/yr)  dU(mm/yr)  # Nome_Stazione\n#\n")
                for i, nome in enumerate(self.nomi):
                    f.write(f"{self.lon[i]:.5f}  {self.lat[i]:.5f}  "
                            f"{self.de[i]:.4f}  {self.dn[i]:.4f}  {self.du[i]:.4f}"
                            f"  # {nome}\n")
            messagebox.showinfo("Esportazione completata",
                                f"File salvato:\n{percorso_out}", parent=self.root)
        except Exception as err:
            messagebox.showerror("Errore di scrittura",
                                 f"Impossibile salvare:\n{err}", parent=self.root)


# =========================================================================
# CLASSE PRINCIPALE – MAPPA INTERATTIVA
# =========================================================================
class MappaInterattivaGNSSMappa:
    def __init__(self, filename):
        self.filename = filename

        # --- lettura dati ---
        self.lon, self.lat, self.de, self.dn, self.du, self.names = [], [], [], [], [], []
        with open(filename, 'r') as f:
            for line in f:
                if not line.strip() or (line.startswith('#') and len(line.split()) < 5):
                    continue
                if '#' in line:
                    data_part, comment_part = line.split('#', 1)
                    name = comment_part.strip()
                else:
                    data_part = line
                    name = f"Sito_{len(self.names)}"
                vals = [float(x) for x in data_part.split()]
                if len(vals) >= 5:
                    self.lon.append(vals[0]); self.lat.append(vals[1])
                    self.de.append(vals[2]);  self.dn.append(vals[3])
                    self.du.append(vals[4]);  self.names.append(name)

        self.lon, self.lat = np.array(self.lon), np.array(self.lat)
        self.de, self.dn, self.du = np.array(self.de), np.array(self.dn), np.array(self.du)
        N = len(self.names)

        # --- proiezione Web Mercator ---
        self.R_web = 6378137.0
        self.x_web = self.R_web * np.radians(self.lon)
        self.y_web = self.R_web * np.log(np.tan(np.pi / 4.0 + np.radians(self.lat) / 2.0))

        # --- stato riferimento ---
        self.ref_idx        = None          
        self.multi_set      = set()         
        self.modo_multi     = False         
        self.modo_eurasia   = False         
        self.modo_adria     = False         
        self.mostra_sigle   = True          # Variabile per gestire la visibilità dei nomi

        # --- stato UI ---
        self._finestra_tab  = None
        self.testi_sigle    = []            # Lista che conterrà i testi sulla mappa

        # ---- figura ----
        self.fig, self.ax = plt.subplots(figsize=(13, 11))
        
        # Aumentato il margine inferiore per lasciare spazio a freccia e bottoni
        self.fig.subplots_adjust(bottom=0.12)

        self.ax.set_xlim(self.x_web.min() - 2000, self.x_web.max() + 2000)
        self.ax.set_ylim(self.y_web.min() - 2000, self.y_web.max() + 2000)

        ctx.add_basemap(self.ax, source=ctx.providers.CartoDB.PositronNoLabels)

        # scatter principale
        self.sc = self.ax.scatter(
            self.x_web, self.y_web, c=self.du, cmap='jet', s=220,
            edgecolors='white', linewidths=1.5, alpha=0.85, zorder=3)

        # quiver vettori orizzontali
        self.q = self.ax.quiver(
            self.x_web, self.y_web, self.de, self.dn,
            color='black', edgecolors='white', linewidth=0.5, zorder=8,
            width=0.0018, headwidth=4, headlength=4, headaxislength=3.5)

        # Riposizionata la scala dei vettori: Y = 0.085 in figure coordinates (sopra i bottoni)
        self.qk = self.ax.quiverkey(
            self.q, 0.85, 0.085, 50, '50 mm/yr', labelpos='E',
            coordinates='figure', fontproperties={'weight': 'bold'})

        # marcatore Modalità 1
        self.star, = self.ax.plot(
            [], [], color='white', marker='*', markersize=22,
            markeredgecolor='black', markeredgewidth=2, zorder=5, linestyle='None')

        # marcatori Modalità 2
        self.multi_markers = self.ax.scatter(
            [], [], s=320, facecolors='none',
            edgecolors='yellow', linewidths=2.5, zorder=6, marker='o')
            
        # marcatore polo di rotazione Adria (Modalità 4)
        self.adria_pole_marker, = self.ax.plot(
            [], [], color='magenta', marker='*', markersize=25,
            markeredgecolor='black', markeredgewidth=1.5, zorder=10, linestyle='None')
            
        self.adria_pole_text = self.ax.text(0, 0, ' Polo Adria', color='magenta', 
                                            fontsize=11, fontweight='bold', zorder=10,
                                            ha='left', va='center',
                                            path_effects=[path_effects.withStroke(linewidth=2, foreground="black")])
        self.adria_pole_text.set_visible(False)

        self.cbar = self.fig.colorbar(
            self.sc, ax=self.ax, label='Spostamento Verticale UP (mm)')

        # Salvataggio degli oggetti text per permetterne il toggle di visibilità
        for i in range(N):
            txt = self.ax.text(
                self.x_web[i], self.y_web[i] + 150, self.names[i],
                fontsize=7, ha='center', color='yellow',
                path_effects=[path_effects.withStroke(linewidth=2, foreground="black")],
                zorder=7)
            self.testi_sigle.append(txt)

        self.ax.set_xlabel('Est Web Mercator (m)', fontsize=11)
        self.ax.set_ylabel('Nord Web Mercator (m)', fontsize=11)
        self.ax.grid(True, linestyle='--', alpha=0.15, color='black')
        self.ax.set_aspect('equal')

        # ---- bottoni (posizionati tra 0.02 e 0.065) ----
        ax_btn_tab  = self.fig.add_axes([0.08, 0.02, 0.22, 0.045])
        ax_btn_exp  = self.fig.add_axes([0.33, 0.02, 0.22, 0.045])
        ax_btn_help = self.fig.add_axes([0.58, 0.02, 0.10, 0.045])

        self.btn_tabella  = Button(ax_btn_tab,  '📋  Mostra Tabella',   color='#d0e8ff', hovercolor='#90c0ff')
        self.btn_esporta  = Button(ax_btn_exp,  '💾  Esporta Velocità', color='#d0ffd8', hovercolor='#80e880')
        self.btn_help     = Button(ax_btn_help, '❓ Aiuto',             color='#fff0c0', hovercolor='#ffe060')

        self.btn_tabella.on_clicked(self._mostra_tabella)
        self.btn_esporta.on_clicked(self._esporta_diretta)
        self.btn_help.on_clicked(lambda e: mostra_aiuto())

        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('key_press_event',    self.on_key)

        self.aggiorna_mappa()

    # ==================================================================
    # CALCOLO VELOCITÀ CORRENTI E POSIZIONE DEL POLO
    # ==================================================================
    def _velocita_correnti(self):
        R_mm = 6378137.0 * 1000.0  
        rad_lat = np.radians(self.lat)
        rad_lon = np.radians(self.lon)

        if self.modo_eurasia or self.modo_adria:
            # POLO EURASIA (ITRF2014) 
            mas2rad = np.pi / (180.0 * 3600.0 * 1000.0)
            Omega_X_eu = -0.085 * mas2rad
            Omega_Y_eu = -0.531 * mas2rad
            Omega_Z_eu =  0.770 * mas2rad
            
            V_N_eu = R_mm * (Omega_X_eu * np.sin(rad_lon) - Omega_Y_eu * np.cos(rad_lon))
            V_E_eu = R_mm * (Omega_Z_eu * np.cos(rad_lat) - Omega_X_eu * np.sin(rad_lat) * np.cos(rad_lon) - Omega_Y_eu * np.sin(rad_lat) * np.sin(rad_lon))

            if self.modo_eurasia and not self.modo_adria:
                de_res = self.de - V_E_eu
                dn_res = self.dn - V_N_eu
                desc = "Velocità Eurasia-Fixed (ITRF2014 PMM - Altamimi et al., 2017)"
                return de_res, dn_res, self.du, desc

            # POLO RELATIVO ADRIA-EURASIA (D'Agostino et al., 2008)
            omega_ad_rad = np.radians(0.309 / 1e6)
            lat_ad_rad = np.radians(45.790)
            lon_ad_rad = np.radians(7.780)

            Omega_X_ad = omega_ad_rad * np.cos(lat_ad_rad) * np.cos(lon_ad_rad)
            Omega_Y_ad = omega_ad_rad * np.cos(lat_ad_rad) * np.sin(lon_ad_rad)
            Omega_Z_ad = omega_ad_rad * np.sin(lat_ad_rad)

            V_N_ad = R_mm * (Omega_X_ad * np.sin(rad_lon) - Omega_Y_ad * np.cos(rad_lon))
            V_E_ad = R_mm * (Omega_Z_ad * np.cos(rad_lat) - Omega_X_ad * np.sin(rad_lat) * np.cos(rad_lon) - Omega_Y_ad * np.sin(rad_lat) * np.sin(rad_lon))

            de_res = self.de - V_E_eu - V_E_ad
            dn_res = self.dn - V_N_eu - V_N_ad
            desc = "Residui Adria-Fixed (Rigoroso: ITRF2014->Eurasia->Adria - D'Agostino et al., 2008)"
            return de_res, dn_res, self.du, desc

        elif self.modo_multi and self.multi_set:
            idx = list(self.multi_set)
            ref_e = np.mean(self.de[idx])
            ref_n = np.mean(self.dn[idx])
            ref_u = np.mean(self.du[idx])
            nomi_gruppo = ", ".join(self.names[i] for i in sorted(idx))
            desc = (f"Velocità relative — riferimento MULTI-STAZIONE "
                    f"({len(idx)} siti): {nomi_gruppo}  "
                    f"[media: dE={ref_e:.2f} dN={ref_n:.2f} dU={ref_u:.2f} mm/yr]")
            return self.de - ref_e, self.dn - ref_n, self.du - ref_u, desc

        elif self.ref_idx is not None:
            desc = f"Velocità relative — stazione di riferimento: {self.names[self.ref_idx]}"
            return (self.de - self.de[self.ref_idx],
                    self.dn - self.dn[self.ref_idx],
                    self.du - self.du[self.ref_idx],
                    desc)
        
        else:
            return self.de.copy(), self.dn.copy(), self.du.copy(), "Velocità assolute input (ITRF2014)"

    # ==================================================================
    # AGGIORNAMENTO MAPPA
    # ==================================================================
    def aggiorna_mappa(self):
        de_r, dn_r, du_r, desc = self._velocita_correnti()

        self.q.set_UVC(de_r, dn_r)
        self.sc.set_array(du_r)
        self.sc.set_clim(vmin=du_r.min(), vmax=du_r.max())

        if self.ref_idx is not None and not (self.modo_multi or self.modo_eurasia or self.modo_adria):
            self.star.set_data([self.x_web[self.ref_idx]], [self.y_web[self.ref_idx]])
        else:
            self.star.set_data([], [])

        if self.modo_multi and self.multi_set:
            idx = list(self.multi_set)
            self.multi_markers.set_offsets(
                np.c_[self.x_web[idx], self.y_web[idx]])
        else:
            self.multi_markers.set_offsets(np.empty((0, 2)))

        # Visualizzazione del Polo di Adria
        if self.modo_adria:
            lat_pole_adria = 45.790
            lon_pole_adria = 7.780
            x_pole = self.R_web * np.radians(lon_pole_adria)
            y_pole = self.R_web * np.log(np.tan(np.pi / 4.0 + np.radians(lat_pole_adria) / 2.0))
            
            self.adria_pole_marker.set_data([x_pole], [y_pole])
            self.adria_pole_text.set_position((x_pole + 10000, y_pole)) 
            self.adria_pole_text.set_visible(True)
            stato_modo = "[MODO 4: ADRIA RIGOROSO] Residui deformativi netti | [A] esci | [R] reset"
        else:
            self.adria_pole_marker.set_data([], [])
            self.adria_pole_text.set_visible(False)
            if self.modo_eurasia:
                stato_modo = "[MODO 3: EURASIA-FIXED] Dinamica rispetto placca EURA | [E] esci | [R] reset"
            elif self.modo_multi:
                n = len(self.multi_set)
                stato_modo = (f"[MODO 2: MULTI-STAZIONE] {n} siti scelti "
                              f"(Ctrl+Click) | [M] esci | [R] reset")
            elif self.ref_idx is not None:
                stato_modo = f"[MODO 1] Rif. Singolo: {self.names[self.ref_idx]} | [R] reset"
            else:
                stato_modo = "Vettori ITRF2014 | [M] Multi | [E] Eurasia | [A] Polo Adria (Rig.)"

        # Aggiunta dell'indicazione del tasto per le sigle nel titolo
        titolo = (f"{stato_modo}\n"
                  f"[+][-] zoom  [T] tabella  [S] sigle  [R] svuota/reset  [?] aiuto")
        self.ax.set_title(titolo, fontsize=10, fontweight='bold', pad=15)
        self.fig.canvas.draw()

        if self._finestra_tab is not None:
            try:
                self._finestra_tab.root.winfo_exists()
                self._mostra_tabella()
            except Exception:
                self._finestra_tab = None

    def _mostra_tabella(self, event=None):
        de, dn, du, desc = self._velocita_correnti()
        if self._finestra_tab is not None:
            try:
                self._finestra_tab.root.destroy()
            except Exception:
                pass
        self._finestra_tab = FinestraTabella(
            nomi=self.names, lon=self.lon, lat=self.lat,
            de=de, dn=dn, du=du,
            descrizione_riferimento=desc,
            percorso_input=self.filename)

    def _esporta_diretta(self, event=None):
        de, dn, du, desc = self._velocita_correnti()
        cartella_default = os.path.dirname(self.filename)
        tag = desc.replace(" ", "_").replace(":", "").replace("->","-")[:40]
        nome_default = f"velocita_{tag}.txt"

        root_tmp = tk.Tk(); root_tmp.withdraw()
        root_tmp.attributes('-topmost', True)
        percorso_out = filedialog.asksaveasfilename(
            title="Salva velocità GNSS",
            initialdir=cartella_default, initialfile=nome_default,
            defaultextension=".txt",
            filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
        )
        root_tmp.destroy()
        if not percorso_out:
            return

        try:
            with open(percorso_out, 'w') as f:
                f.write(f"# {desc}\n")
                f.write("# Formato: Lon(°)  Lat(°)  dE(mm/yr)  dN(mm/yr)  dU(mm/yr)  # Nome_Stazione\n#\n")
                for i, nome in enumerate(self.names):
                    f.write(f"{self.lon[i]:.5f}  {self.lat[i]:.5f}  "
                            f"{de[i]:.4f}  {dn[i]:.4f}  {du[i]:.4f}"
                            f"  # {nome}\n")
            self.ax.set_title(
                f"✅ File salvato: {os.path.basename(percorso_out)}\n"
                "(la mappa si aggiornerà al prossimo click/tasto)",
                fontsize=10, color="darkgreen")
            self.fig.canvas.draw()
        except Exception as err:
            root_err = tk.Tk(); root_err.withdraw()
            messagebox.showerror("Errore di scrittura", f"Impossibile salvare:\n{err}")
            root_err.destroy()

    def on_click(self, event):
        if self.fig.canvas.manager.toolbar.mode != '':
            return
        if event.inaxes != self.ax:
            return

        distanze = (self.x_web - event.xdata)**2 + (self.y_web - event.ydata)**2
        sito_vicino = np.argmin(distanze)
        x_range = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        soglia = (x_range * 0.03)**2

        if distanze[sito_vicino] >= soglia:
            return   

        if self.modo_multi and event.key == 'control':
            if sito_vicino in self.multi_set:
                self.multi_set.discard(sito_vicino)
            else:
                self.multi_set.add(sito_vicino)
            self.aggiorna_mappa()

        elif not self.modo_multi:
            self.ref_idx = sito_vicino
            self.modo_eurasia = False
            self.modo_adria = False
            self.aggiorna_mappa()

    def on_key(self, event):
        if event.key in ['r', 'R']:
            self.ref_idx   = None
            self.multi_set = set()
            self.modo_eurasia = False
            self.modo_adria = False
            self.aggiorna_mappa()

        elif event.key in ['m', 'M']:
            self.modo_multi = not self.modo_multi
            if self.modo_multi:
                self.modo_eurasia = False
                self.modo_adria = False
            else:
                self.multi_set = set()
            self.aggiorna_mappa()

        elif event.key in ['e', 'E']:
            self.modo_eurasia = not self.modo_eurasia
            if self.modo_eurasia:
                self.modo_multi = False
                self.modo_adria = False
                self.ref_idx = None
            self.aggiorna_mappa()

        elif event.key in ['a', 'A']:
            self.modo_adria = not self.modo_adria
            if self.modo_adria:
                self.modo_multi = False
                self.modo_eurasia = False
                self.ref_idx = None
            self.aggiorna_mappa()

        # Funzionalità per il toggle della visibilità delle sigle
        elif event.key in ['s', 'S']:
            self.mostra_sigle = not self.mostra_sigle
            for txt in self.testi_sigle:
                txt.set_visible(self.mostra_sigle)
            self.fig.canvas.draw()

        elif event.key in ['t', 'T']:
            self._mostra_tabella()

        elif event.key in ['?']:
            mostra_aiuto()

        elif event.key in ['+', '=']:
            if getattr(self.q, 'scale', None) is None:
                self.q.scale = 1.0
            self.q.scale *= 0.8
            self.fig.canvas.draw()

        elif event.key == '-':
            if getattr(self.q, 'scale', None) is None:
                self.q.scale = 1.0
            self.q.scale *= 1.25
            self.fig.canvas.draw()


if __name__ == '__main__':
    percorso_file = seleziona_file_input()

    if percorso_file is None:
        if getattr(sys, 'frozen', False):
            cartella_corrente = os.path.dirname(sys.executable)
        else:
            cartella_corrente = os.path.dirname(os.path.abspath(__file__))
        percorso_file = os.path.join(cartella_corrente, 'gnss_rino_input.txt')
        if not os.path.exists(percorso_file):
            print(f"[ERRORE] Nessun file selezionato e file di default non trovato:\n  {percorso_file}")
            input("\nPremi INVIO per uscire...")
            sys.exit()

    if not os.path.exists(percorso_file):
        print(f"[ERRORE] Impossibile trovare il file: {percorso_file}")
        input("\nPremi INVIO per uscire...")
        sys.exit()

    mappa = MappaInterattivaGNSSMappa(percorso_file)
    plt.show()