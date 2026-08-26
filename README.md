# ABF Data Analysis Code

Interactive Python tool for analysing contractile force recordings from living myocardial slices (LMS) stored in Axon Binary Format (`.abf`) files. It was written during my PhD at Imperial College London to extract per-twitch contractility parameters from paced force/stimulus recordings and export them as CSV tables.

Given an `.abf` file containing a force channel (channel 0) and a stimulus/voltage channel (channel 1), the tool lets you review the recording, position analysis windows around experimental tags, detect force and stimulus peaks, and computes for every twitch:

| Parameter | Definition in the code |
|---|---|
| Active force | Force at each detected force peak, normalised to slice cross-sectional area (mN/mm²) |
| Passive force | Force at the moment of each stimulus peak (i.e. immediately before the twitch) |
| Amplitude | Active force − passive force |
| Time to peak | Delay from stimulus peak to the next force peak (ms) |
| Time to 50% / 90% decay | Time from force peak until force falls to 50% / 10% of amplitude above passive (ms) |
| Tau (τ) | Time constant of a single exponential `a·exp(−t/τ) + c` fitted to the decay from 50% relaxation, over up to 500 ms or until the next stimulus |

Force is normalised by cross-sectional area = slice width × 0.3 mm (assumed slice thickness of 300 µm). The default width is 3.33 mm and can be changed in the GUI.

## Files

- `Peak_analysis.py` — main script; run this.
- `draggable_line.py` — helper class that makes the tag markers draggable on the matplotlib plot. Must be in the same folder as `Peak_analysis.py`.

## Requirements

- Python 3.8 or later
- A desktop environment: the tool uses Tk dialogs and interactive matplotlib windows, so it will not run headless.
- Python packages: `pyabf`, `numpy`, `scipy`, `pandas`, `matplotlib`

Install the packages with:

```bash
pip install -r requirements.txt
```

`tkinter` ships with the standard Python installer on Windows and macOS. On Debian/Ubuntu you may need `sudo apt install python3-tk`.

## Running the analysis

```bash
python Peak_analysis.py
```

The workflow is entirely dialog-driven:

1. **Select file.** A file picker asks for an `.abf` file.
2. **Review the trace.** The force channel is plotted with a red vertical line at each tag recorded during the experiment. Tag times are multiplied by a correction factor (default 2.0) to compensate for the timing offset in the acquisition setup. Scroll to zoom the x-axis, Ctrl+scroll to zoom the y-axis, middle-mouse drag to pan, and drag any red line to reposition a tag.
   - *Set Slice Width* — enter the slice width in mm used for force normalisation.
   - *Calibrate Tag Timepoints* — change the tag correction factor.
   - *Reset Tags to Original Position* — discard manual tag adjustments.
   - *Confirm Analysis Timepoints* — proceed to analysis.
3. **Define analysis windows.** A table lists each tag with an editable start time and duration (default 7 s). Overlapping windows are flagged.
4. **Detect peaks.** For each window, force peaks and then stimulus peaks are detected with `scipy.signal.find_peaks`. A dialog lets you adjust height, minimum distance and prominence and shows the result until you accept it.
5. **Confirm the fit.** An annotated plot shows the detected peaks, decay points and fitted exponentials for the window. Accept it, or go back and re-detect peaks.
6. **Export.** Results are appended to `peak_statistics.csv` (one row per twitch) and a per-window summary (mean, SEM, n for each parameter) is written to `summary_statistics.csv`. Both files are created in the directory the script is run from.

## Output columns

`peak_statistics.csv`: `Timepoints`, `Time to Peak`, `Time to 50% Decay`, `Time to 90% Decay`, `Tau`, `Active Force`, `Passive Force`, `Amplitude`

`summary_statistics.csv`: for each of the parameters above, `<parameter>_mean`, `<parameter>_sem`, `<parameter>_count`, grouped by analysis window.

Times are in milliseconds, forces in mN/mm², tau in seconds.

## Author

Barrett Downing, National Heart and Lung Institute, Imperial College London. Written as part of my PhD (2019–2024) on the role of mechanical load in the developing myocardium, using living myocardial slices.

Thesis: *link to be added once deposited in Spiral (Imperial's repository)*

Questions and bug reports are welcome via [GitHub Issues](https://github.com/bdowning87/ABF-Data-Analysis-Code/issues).

## Citing

If you use this code, please cite it via the DOI on the release (see the *Cite this repository* button on GitHub, or `CITATION.cff`).

## Licence

MIT — see `LICENSE`.
