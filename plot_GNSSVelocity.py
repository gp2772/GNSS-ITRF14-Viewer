import os
import sys
import site
import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.widgets import Button
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk

# Suppress generic matplotlib/contextily warnings in the terminal
warnings.filterwarnings("ignore")

# =========================================================================
# PROJ.DB & ENVIRONMENT FAILSAFE (NO-IMPORT APPROACH)
# =========================================================================
def setup_proj_environment():
    """
    Finds proj.db WITHOUT importing rasterio/pyproj.
    Importing them before setting PROJ_LIB freezes the C-extension 
    with empty/wrong environment variables, causing a crash.
    """
    search_paths = []
    
    # Add PyInstaller temp path if running as a compiled .exe
    if getattr(sys, 'frozen', False):
        search_paths.append(sys._MEIPASS)
    
    # Add system and user site-packages (where pip installs libraries)
    search_paths.extend(site.getsitepackages())
    if hasattr(site, 'getusersitepackages'):
        search_paths.append(site.getusersitepackages())
        
    for sp in search_paths:
        candidates = [
            os.path.join(sp, "rasterio", "proj_data"),
            os.path.join(sp, "pyproj", "proj_dir", "share", "proj"),
            os.path.join(sp, "osgeo", "data", "proj")
        ]
        for c in candidates:
            # Check if proj.db actually exists in this folder
            if os.path.isfile(os.path.join(c, "proj.db")):
                os.environ['PROJ_LIB'] = c
                os.environ['PROJ_DATA'] = c
                return

setup_proj_environment()
# =========================================================================

# Now it is safe to import contextily and its rasterio backend
try:
    import contextily as ctx
except ImportError as e:
    print(f"\n[ERROR] Problem with contextily or dependencies: {e}\n")
    input("Press ENTER to exit...")
    sys.exit()

# =========================================================================
# INPUT FILE SELECTION (FILE EXPLORER)
# =========================================================================
def select_input_file():
    """Opens a file dialog to select the GNSS input file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    filepath = filedialog.askopenfilename(
        title="Select GNSS velocity file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    root.destroy()
    return filepath if filepath else None

# =========================================================================
# HELP WINDOW
# =========================================================================
HELP_TEXT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          USER GUIDE – GNSS Velocity Viewer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODE 1 – SINGLE STATION REFERENCE
──────────────────────────────────────────
  • Left Click on a site  →  Sets a single station as the reference.
    Subtracts its absolute velocity from the entire network.

MODE 2 – REGIONAL REFERENCE (MULTI-STATION)
───────────────────────────────────────────────────
  • [M]  →  Toggle multi-station mode (inner constraint).
  • Ctrl+Click on multiple sites to add them to the reference group.
    Subtracts the weighted average of the selected group.

MODE 3 – EURASIA REFERENCE (ITRF2014)
───────────────────────────────────────────────────
  • [E]  →  Subtracts on-the-fly the Eurasian plate rotation pole, 
            using the ITRF2014 PMM model (Altamimi et al., 2017).

MODE 4 – ADRIA POLE REFERENCE (RIGOROUS APPROACH)
───────────────────────────────────────────────────
  • [A]  →  Applies a two-stage kinematic filtering:
             1. Subtracts the absolute frame ITRF2014 -> Eurasia
             2. Subtracts the relative pole Eurasia -> Adria (D'Agostino et al., 2008)
            The pole position (45.790°N, 7.780°E) is displayed
            with a magenta star on the map.

MAP NAVIGATION
─────────────────
  Shortcuts:
    [+] or [=]  →  Increase vector arrow scale
    [-]         →  Decrease vector arrow scale
    [T]         →  Open data table with current values
    [M]         →  Toggle Multi-station Mode
    [E]         →  Toggle Eurasia Plate (ITRF2014)
    [A]         →  Toggle Adria Microplate (Rigorous ITRF2014)
    [S]         →  Show / Hide station labels
    [R]         →  Reset (revert to absolute ITRF vectors)
    [?]         →  Show this guide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def show_help():
    """Displays the user guide in a separate Tkinter window."""
    win = tk.Toplevel()
    win.title("Guide – GNSS Velocity Viewer")
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

    txt.insert(tk.END, HELP_TEXT)
    txt.configure(state=tk.DISABLED)

    tk.Button(win, text="Close", command=win.destroy,
              bg="#c0c0c0", font=("Arial", 10)).pack(pady=(0, 8))

# =========================================================================
# VELOCITY TABLE WINDOW
# =========================================================================
class TableWindow:
    """Tkinter window to display current velocities and export them to a file."""
    def __init__(self, names, lon, lat, de, dn, du, reference_desc, input_path):
        self.names = names
        self.lon = lon
        self.lat = lat
        self.de = de
        self.dn = dn
        self.du = du
        self.reference_desc = reference_desc
        self.input_path = input_path

        self.root = tk.Toplevel()
        self.root.title("GNSS Velocity Table")
        self.root.resizable(True, True)
        self._build_ui()

    def _build_ui(self):
        state_label = self.reference_desc or "Absolute velocities"
        tk.Label(self.root, text=state_label, font=("Arial", 10, "bold"),
                 fg="navy", wraplength=560).pack(pady=(8, 2), padx=10)

        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        cols = ("Station", "Lon (°)", "Lat (°)", "dE (mm/yr)", "dN (mm/yr)", "dU (mm/yr)")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)

        for col, width in zip(cols, [110, 90, 90, 90, 90, 90]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")

        sy = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("even", background="#f0f4ff")
        self.tree.tag_configure("odd",  background="#ffffff")

        for i, name in enumerate(self.names):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", tk.END, values=(
                name,
                f"{self.lon[i]:.5f}", f"{self.lat[i]:.5f}",
                f"{self.de[i]:.4f}",  f"{self.dn[i]:.4f}",  f"{self.du[i]:.4f}",
            ), tags=(tag,))

        tk.Button(
            self.root, text="💾  Export velocities to .txt",
            command=self._export, bg="#2060a0", fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT, padx=10, pady=6
        ).pack(pady=(4, 10))

    def _export(self):
        """Handles the logic for exporting the current table to a text file."""
        default_folder = os.path.dirname(self.input_path)
        tag_name = (self.reference_desc or "absolute") \
                       .replace(" ", "_").replace(":", "").replace("->","-")[:40]
        default_name = f"velocities_{tag_name}.txt"

        root_tmp = tk.Tk(); root_tmp.withdraw()
        root_tmp.attributes('-topmost', True)
        out_path = filedialog.asksaveasfilename(
            title="Save GNSS velocities",
            initialdir=default_folder, initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        root_tmp.destroy()
        if not out_path:
            return

        try:
            with open(out_path, 'w') as f:
                f.write(f"# {self.reference_desc or 'Absolute GNSS Velocities'}\n")
                f.write("# Format: Lon(°)  Lat(°)  dE(mm/yr)  dN(mm/yr)  dU(mm/yr)  # Station_Name\n#\n")
                for i, name in enumerate(self.names):
                    f.write(f"{self.lon[i]:.5f}  {self.lat[i]:.5f}  "
                            f"{self.de[i]:.4f}  {self.dn[i]:.4f}  {self.du[i]:.4f}"
                            f"  # {name}\n")
            messagebox.showinfo("Export complete",
                                f"File saved successfully:\n{out_path}", parent=self.root)
        except Exception as err:
            messagebox.showerror("Write Error",
                                 f"Unable to save file:\n{err}", parent=self.root)

# =========================================================================
# MAIN CLASS – INTERACTIVE MAP
# =========================================================================
class InteractiveGNSSMap:
    def __init__(self, filename):
        self.filename = filename

        # --- Read data ---
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
                    name = f"Site_{len(self.names)}"
                vals = [float(x) for x in data_part.split()]
                if len(vals) >= 5:
                    self.lon.append(vals[0]); self.lat.append(vals[1])
                    self.de.append(vals[2]);  self.dn.append(vals[3])
                    self.du.append(vals[4]);  self.names.append(name)

        self.lon, self.lat = np.array(self.lon), np.array(self.lat)
        self.de, self.dn, self.du = np.array(self.de), np.array(self.dn), np.array(self.du)
        N = len(self.names)

        # --- Web Mercator projection ---
        self.R_web = 6378137.0
        self.x_web = self.R_web * np.radians(self.lon)
        self.y_web = self.R_web * np.log(np.tan(np.pi / 4.0 + np.radians(self.lat) / 2.0))

        # --- Reference states ---
        self.ref_idx        = None          
        self.multi_set      = set()         
        self.mode_multi     = False         
        self.mode_eurasia   = False         
        self.mode_adria     = False         
        self.show_labels    = True          # Manage label visibility

        # --- UI state ---
        self._table_window  = None
        self.label_texts    = []            # List holding text objects

        # ---- Figure setup ----
        self.fig, self.ax = plt.subplots(figsize=(14, 9))
        
        # Rename the window to remove the default "Figure 1"
        self.fig.canvas.manager.set_window_title("GNSS Velocity Viewer - ITRF2014")
        
        # Layout optimization: expands the map and leaves dedicated space at the bottom for buttons
        self.fig.subplots_adjust(left=0.06, right=0.92, top=0.92, bottom=0.15)

        self.ax.set_xlim(self.x_web.min() - 2000, self.x_web.max() + 2000)
        self.ax.set_ylim(self.y_web.min() - 2000, self.y_web.max() + 2000)

        # Neutral Esri basemap to avoid OpenStreetMap 403 blocks and make vectors pop
        ctx.add_basemap(self.ax, crs="EPSG:3857", source=ctx.providers.Esri.WorldGrayCanvas)

        # Main scatter (vertical displacement)
        self.sc = self.ax.scatter(
            self.x_web, self.y_web, c=self.du, cmap='jet', s=220,
            edgecolors='white', linewidths=1.5, alpha=0.85, zorder=3)

        # Horizontal velocity quiver
        self.q = self.ax.quiver(
            self.x_web, self.y_web, self.de, self.dn,
            color='black', edgecolors='white', linewidth=0.5, zorder=8,
            width=0.0018, headwidth=4, headlength=4, headaxislength=3.5)

        # Quiver scale key cleanly positioned at the bottom right
        self.qk = self.ax.quiverkey(
            self.q, 0.88, 0.05, 50, '50 mm/yr', labelpos='E',
            coordinates='figure', fontproperties={'weight': 'bold'})

        # Mode 1 marker (Single Station)
        self.star, = self.ax.plot(
            [], [], color='white', marker='*', markersize=22,
            markeredgecolor='black', markeredgewidth=2, zorder=5, linestyle='None')

        # Mode 2 markers (Multi-Station)
        self.multi_markers = self.ax.scatter(
            [], [], s=320, facecolors='none',
            edgecolors='yellow', linewidths=2.5, zorder=6, marker='o')
            
        # Adria Pole marker (Mode 4)
        self.adria_pole_marker, = self.ax.plot(
            [], [], color='magenta', marker='*', markersize=25,
            markeredgecolor='black', markeredgewidth=1.5, zorder=10, linestyle='None')
            
        self.adria_pole_text = self.ax.text(0, 0, ' Adria Pole', color='magenta', 
                                            fontsize=11, fontweight='bold', zorder=10,
                                            ha='left', va='center',
                                            path_effects=[path_effects.withStroke(linewidth=2, foreground="black")])
        self.adria_pole_text.set_visible(False)

        # Colorbar
        self.cbar = self.fig.colorbar(
            self.sc, ax=self.ax, label='Vertical Displacement UP (mm)')

        # Station labels setup
        for i in range(N):
            txt = self.ax.text(
                self.x_web[i], self.y_web[i] + 150, self.names[i],
                fontsize=7, ha='center', color='yellow',
                path_effects=[path_effects.withStroke(linewidth=2, foreground="black")],
                zorder=7)
            self.label_texts.append(txt)

        self.ax.set_xlabel('East Web Mercator (m)', fontsize=11)
        self.ax.set_ylabel('North Web Mercator (m)', fontsize=11)
        self.ax.grid(True, linestyle='--', alpha=0.15, color='black')
        self.ax.set_aspect('equal')

        # ---- Buttons (Centered and aligned in the bottom margin) ----
        ax_btn_tab  = self.fig.add_axes([0.15, 0.04, 0.18, 0.05])
        ax_btn_exp  = self.fig.add_axes([0.35, 0.04, 0.18, 0.05])
        ax_btn_help = self.fig.add_axes([0.55, 0.04, 0.10, 0.05])

        self.btn_table   = Button(ax_btn_tab,  '📋  Show Table',      color='#d0e8ff', hovercolor='#90c0ff')
        self.btn_export  = Button(ax_btn_exp,  '💾  Export Velocities', color='#d0ffd8', hovercolor='#80e880')
        self.btn_help    = Button(ax_btn_help, '❓ Help',             color='#fff0c0', hovercolor='#ffe060')

        self.btn_table.on_clicked(self._show_table)
        self.btn_export.on_clicked(self._export_direct)
        self.btn_help.on_clicked(lambda e: show_help())

        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('key_press_event',    self.on_key)

        self.update_map()

    # ==================================================================
    # CALCULATE CURRENT VELOCITIES AND POLE POSITION
    # ==================================================================
    def _current_velocities(self):
        R_mm = 6378137.0 * 1000.0  
        rad_lat = np.radians(self.lat)
        rad_lon = np.radians(self.lon)

        if self.mode_eurasia or self.mode_adria:
            # EURASIA POLE (ITRF2014) 
            mas2rad = np.pi / (180.0 * 3600.0 * 1000.0)
            Omega_X_eu = -0.085 * mas2rad
            Omega_Y_eu = -0.531 * mas2rad
            Omega_Z_eu =  0.770 * mas2rad
            
            V_N_eu = R_mm * (Omega_X_eu * np.sin(rad_lon) - Omega_Y_eu * np.cos(rad_lon))
            V_E_eu = R_mm * (Omega_Z_eu * np.cos(rad_lat) - Omega_X_eu * np.sin(rad_lat) * np.cos(rad_lon) - Omega_Y_eu * np.sin(rad_lat) * np.sin(rad_lon))

            if self.mode_eurasia and not self.mode_adria:
                de_res = self.de - V_E_eu
                dn_res = self.dn - V_N_eu
                desc = "Eurasia-Fixed Velocities (ITRF2014 PMM - Altamimi et al., 2017)"
                return de_res, dn_res, self.du, desc

            # RELATIVE ADRIA-EURASIA POLE (D'Agostino et al., 2008)
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
            desc = "Adria-Fixed Residuals (Rigorous: ITRF2014->Eurasia->Adria - D'Agostino et al., 2008)"
            return de_res, dn_res, self.du, desc

        elif self.mode_multi and self.multi_set:
            idx = list(self.multi_set)
            ref_e = np.mean(self.de[idx])
            ref_n = np.mean(self.dn[idx])
            ref_u = np.mean(self.du[idx])
            group_names = ", ".join(self.names[i] for i in sorted(idx))
            desc = (f"Relative velocities — MULTI-STATION reference "
                    f"({len(idx)} sites): {group_names}  "
                    f"[mean: dE={ref_e:.2f} dN={ref_n:.2f} dU={ref_u:.2f} mm/yr]")
            return self.de - ref_e, self.dn - ref_n, self.du - ref_u, desc

        elif self.ref_idx is not None:
            desc = f"Relative velocities — reference station: {self.names[self.ref_idx]}"
            return (self.de - self.de[self.ref_idx],
                    self.dn - self.dn[self.ref_idx],
                    self.du - self.du[self.ref_idx],
                    desc)
        
        else:
            return self.de.copy(), self.dn.copy(), self.du.copy(), "Absolute input velocities (ITRF2014)"

    # ==================================================================
    # UPDATE MAP RENDERING
    # ==================================================================
    def update_map(self):
        de_r, dn_r, du_r, desc = self._current_velocities()

        self.q.set_UVC(de_r, dn_r)
        self.sc.set_array(du_r)
        self.sc.set_clim(vmin=du_r.min(), vmax=du_r.max())

        if self.ref_idx is not None and not (self.mode_multi or self.mode_eurasia or self.mode_adria):
            self.star.set_data([self.x_web[self.ref_idx]], [self.y_web[self.ref_idx]])
        else:
            self.star.set_data([], [])

        if self.mode_multi and self.multi_set:
            idx = list(self.multi_set)
            self.multi_markers.set_offsets(
                np.c_[self.x_web[idx], self.y_web[idx]])
        else:
            self.multi_markers.set_offsets(np.empty((0, 2)))

        # Display Adria Pole
        if self.mode_adria:
            lat_pole_adria = 45.790
            lon_pole_adria = 7.780
            x_pole = self.R_web * np.radians(lon_pole_adria)
            y_pole = self.R_web * np.log(np.tan(np.pi / 4.0 + np.radians(lat_pole_adria) / 2.0))
            
            self.adria_pole_marker.set_data([x_pole], [y_pole])
            self.adria_pole_text.set_position((x_pole + 10000, y_pole)) 
            self.adria_pole_text.set_visible(True)
            mode_status = "[MODE 4: RIGOROUS ADRIA] Net deformational residuals | [A] exit | [R] reset"
        else:
            self.adria_pole_marker.set_data([], [])
            self.adria_pole_text.set_visible(False)
            if self.mode_eurasia:
                mode_status = "[MODE 3: EURASIA-FIXED] Dynamics relative to EURA plate | [E] exit | [R] reset"
            elif self.mode_multi:
                n = len(self.multi_set)
                mode_status = (f"[MODE 2: MULTI-STATION] {n} sites chosen "
                              f"(Ctrl+Click) | [M] exit | [R] reset")
            elif self.ref_idx is not None:
                mode_status = f"[MODE 1] Single Ref: {self.names[self.ref_idx]} | [R] reset"
            else:
                mode_status = "ITRF2014 Vectors | [M] Multi | [E] Eurasia | [A] Adria Pole (Rig.)"

        # Construct title with instructions
        title_text = (f"{mode_status}\n"
                      f"[+][-] zoom  [T] table  [S] labels  [R] reset/clear  [?] help")
        self.ax.set_title(title_text, fontsize=10, fontweight='bold', pad=15)
        self.fig.canvas.draw()

        if self._table_window is not None:
            try:
                self._table_window.root.winfo_exists()
                self._show_table()
            except Exception:
                self._table_window = None

    def _show_table(self, event=None):
        de, dn, du, desc = self._current_velocities()
        if self._table_window is not None:
            try:
                self._table_window.root.destroy()
            except Exception:
                pass
        self._table_window = TableWindow(
            names=self.names, lon=self.lon, lat=self.lat,
            de=de, dn=dn, du=du,
            reference_desc=desc,
            input_path=self.filename)

    def _export_direct(self, event=None):
        de, dn, du, desc = self._current_velocities()
        default_folder = os.path.dirname(self.filename)
        tag = desc.replace(" ", "_").replace(":", "").replace("->","-")[:40]
        default_name = f"velocities_{tag}.txt"

        root_tmp = tk.Tk(); root_tmp.withdraw()
        root_tmp.attributes('-topmost', True)
        out_path = filedialog.asksaveasfilename(
            title="Save GNSS velocities",
            initialdir=default_folder, initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        root_tmp.destroy()
        if not out_path:
            return

        try:
            with open(out_path, 'w') as f:
                f.write(f"# {desc}\n")
                f.write("# Format: Lon(°)  Lat(°)  dE(mm/yr)  dN(mm/yr)  dU(mm/yr)  # Station_Name\n#\n")
                for i, name in enumerate(self.names):
                    f.write(f"{self.lon[i]:.5f}  {self.lat[i]:.5f}  "
                            f"{de[i]:.4f}  {dn[i]:.4f}  {du[i]:.4f}"
                            f"  # {name}\n")
            self.ax.set_title(
                f"✅ File saved: {os.path.basename(out_path)}\n"
                "(the map will update on the next click/keypress)",
                fontsize=10, color="darkgreen")
            self.fig.canvas.draw()
        except Exception as err:
            root_err = tk.Tk(); root_err.withdraw()
            messagebox.showerror("Write Error", f"Unable to save:\n{err}")
            root_err.destroy()

    def on_click(self, event):
        # Ignore clicks if pan/zoom tools are active
        if self.fig.canvas.manager.toolbar.mode != '':
            return
        if event.inaxes != self.ax:
            return

        distances = (self.x_web - event.xdata)**2 + (self.y_web - event.ydata)**2
        closest_site = np.argmin(distances)
        x_range = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        threshold = (x_range * 0.03)**2

        # Ignore clicks that are too far from any station
        if distances[closest_site] >= threshold:
            return   

        if self.mode_multi and event.key == 'control':
            if closest_site in self.multi_set:
                self.multi_set.discard(closest_site)
            else:
                self.multi_set.add(closest_site)
            self.update_map()

        elif not self.mode_multi:
            self.ref_idx = closest_site
            self.mode_eurasia = False
            self.mode_adria = False
            self.update_map()

    def on_key(self, event):
        if event.key in ['r', 'R']:
            self.ref_idx   = None
            self.multi_set = set()
            self.mode_eurasia = False
            self.mode_adria = False
            self.update_map()

        elif event.key in ['m', 'M']:
            self.mode_multi = not self.mode_multi
            if self.mode_multi:
                self.mode_eurasia = False
                self.mode_adria = False
            else:
                self.multi_set = set()
            self.update_map()

        elif event.key in ['e', 'E']:
            self.mode_eurasia = not self.mode_eurasia
            if self.mode_eurasia:
                self.mode_multi = False
                self.mode_adria = False
                self.ref_idx = None
            self.update_map()

        elif event.key in ['a', 'A']:
            self.mode_adria = not self.mode_adria
            if self.mode_adria:
                self.mode_multi = False
                self.mode_eurasia = False
                self.ref_idx = None
            self.update_map()

        elif event.key in ['s', 'S']:
            self.show_labels = not self.show_labels
            for txt in self.label_texts:
                txt.set_visible(self.show_labels)
            self.fig.canvas.draw()

        elif event.key in ['t', 'T']:
            self._show_table()

        elif event.key in ['?']:
            show_help()

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
    filepath = select_input_file()

    # Fallback to default file if dialogue is cancelled
    if filepath is None:
        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(current_dir, 'vel_EPOS.txt')
        if not os.path.exists(filepath):
            print(f"[ERROR] No file selected and default file not found:\n  {filepath}")
            input("\nPress ENTER to exit...")
            sys.exit()

    if not os.path.exists(filepath):
        print(f"[ERROR] Cannot find file: {filepath}")
        input("\nPress ENTER to exit...")
        sys.exit()

    map_app = InteractiveGNSSMap(filepath)
    plt.show()