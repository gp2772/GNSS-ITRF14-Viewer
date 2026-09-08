# GNSS Velocity Viewer (GNSSvv)

Interactive Python tool for visualizing and analyzing GNSS velocity fields. Features real-time reference frame transformations (ITRF, Eurasia-fixed, Adria-fixed) to isolate local tectonic deformation.

![GNSSvv Map Preview](path/to/your/image.png)


An interactive Python-based viewer for exploring GNSS velocity fields and analyzing crustal kinematics. The tool allows seamless transitions from a global reference frame (ITRF) to regional or local frames to precisely map residual tectonic deformation.

## Key Features

The software offers four real-time kinematic filtering modes:

* **Mode 1 (Single Station):** Subtracts the velocity of a single user-selected site to observe local relative deformation.
* **Mode 2 (Multi-Station):** Subtracts the weighted average of a selected group of stations (inner constraint) to establish an internal reference frame for the network.
* **Mode 3 (Eurasia-Fixed):** Removes the rigid body motion of the Eurasian plate by subtracting the Eulerian pole from the ITRF2014 PMM model (Altamimi et al., 2017).
* **Mode 4 (Adria-Fixed):** Isolates the intraplate deformation of the Apennines and the foreland using a two-stage approach. It first subtracts the Eurasia pole (ITRF2014) and subsequently the relative Eurasia-Adria pole estimated by D'Agostino et al. (2008).

## Prerequisites and Installation

Ensure you have Python 3.x installed on your system. Clone the repository and install the required libraries:

    git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
    cd YOUR_REPO_NAME
    pip install -r requirements.txt

**Main Dependencies (`requirements.txt`):**
* `numpy`
* `matplotlib`
* `contextily`

## Input Data Format

The tool requires a plain text `.txt` file (e.g., velocities extracted from PRIDE PPP-AR) formatted with one station per line. Lines starting with `#` are treated as comments and ignored.

    # Lon(°)  Lat(°)  dE(mm/yr)  dN(mm/yr)  dU(mm/yr)  # Station_Name
    15.33100  41.15900  -2.2608  0.8747  1.2100  # ACCA
    13.38400  41.67300  -3.2778  -1.0175  -0.4800  # ALAT

## Controls and Navigation

The interactive map is fully controlled via the following mouse and keyboard shortcuts:

* **Left Click:** Sets a single station as the reference (Mode 1).
* **[M] + Ctrl+Click:** Activates Mode 2 and adds selected sites to the reference group.
* **[E]:** Toggles the Eurasia plate pole on/off (Mode 3).
* **[A]:** Toggles the Adria microplate pole on/off and displays the pole location on the map.
* **[S]:** Shows/Hides station labels on the map.
* **[+] / [-]:** Increases or decreases the visual scale of the vector arrows.
* **[T]:** Opens an interactive data table displaying the currently calculated residuals.
* **[R]:** Resets the view and reverts to the original absolute ITRF input vectors.

## Exporting Data

By clicking the **"Export Velocities"** button, you can immediately save the currently displayed residual vector field to a new `.txt` file. The output maintains the required formatting, making it ready for subsequent plotting workflows (e.g., using GMT).
