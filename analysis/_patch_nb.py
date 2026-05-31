"""Patch colab_psd_diagnostics.ipynb: Step 8/9 cells to new style."""
import json
from pathlib import Path

NB_PATH = Path(r'c:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\analysis\colab_psd_diagnostics.ipynb')

with NB_PATH.open(encoding='utf-8') as f:
    nb = json.load(f)

# ── Cell 17 (id=fedf8ac1): Step 8 markdown ──────────────────────────────────
STEP8_MD = [
    "## Step 8 — PSD Graph\n",
    "\n",
    "Plots pore volume fraction per bin (left axis) and cumulative pore volume\n",
    "fraction (right axis) vs. pore diameter (µm) on a log-scale x-axis.\n",
    "The 30–150 µm range is highlighted as the **microbial active domain**.\n",
    "\n",
    "Output: `psd_30bins_microbial_active_domain.png`",
]

# ── Cell 18 (id=dda05dc5): Step 8 code ──────────────────────────────────────
STEP8_CODE = [
    "import json, pathlib\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Locate the latest run folder\n",
    "run_folders = sorted(pathlib.Path(OUTPUT_ROOT).glob('psd_diag_*'))\n",
    "if not run_folders:\n",
    "    raise FileNotFoundError(f'No run folders found in {OUTPUT_ROOT}')\n",
    "latest = run_folders[-1]\n",
    "csv_path = latest / 'psd_table.csv'\n",
    "print(f'Reading: {csv_path}')\n",
    "\n",
    "df = pd.read_csv(csv_path)\n",
    "\n",
    "with open(latest / 'result_psd.json') as f:\n",
    "    result_data = json.load(f)\n",
    "\n",
    "bin_edges_um = np.array(result_data.get('bin_edges_um', []))\n",
    "total_pore_voxels = int(result_data.get('total_pore_voxels', df['Volume_Count'].sum()))\n",
    "\n",
    "# Per-bin pore volume fraction\n",
    "diameters = df['Diameter_um'].values\n",
    "volume_fraction = df['Volume_Count'].values / total_pore_voxels\n",
    "cumulative_fraction = np.cumsum(volume_fraction)\n",
    "\n",
    "# Bar widths from bin edges\n",
    "if bin_edges_um.size > 1 and len(bin_edges_um) - 1 == len(df):\n",
    "    bar_widths = np.diff(bin_edges_um)\n",
    "else:\n",
    "    bar_widths = diameters * 0.1\n",
    "\n",
    "# Microbial active domain bounds\n",
    "MICROBIAL_LO, MICROBIAL_HI = 30.0, 150.0\n",
    "bar_colors = ['#e67300' if MICROBIAL_LO <= d <= MICROBIAL_HI else '#4878cf'\n",
    "               for d in diameters]\n",
    "\n",
    "# ── Plot ──────────────────────────────────────────────────────────────────\n",
    "fig, ax1 = plt.subplots(figsize=(11, 6))\n",
    "ax2 = ax1.twinx()\n",
    "\n",
    "ax1.bar(diameters, volume_fraction, width=bar_widths,\n",
    "        color=bar_colors, edgecolor='white', linewidth=0.5, alpha=0.85,\n",
    "        label='Pore volume fraction per bin')\n",
    "\n",
    "ax2.plot(diameters, cumulative_fraction, color='black', linewidth=2,\n",
    "         label='Cumulative')\n",
    "ax2.set_ylim(0, 1.05)\n",
    "ax2.set_ylabel('Cumulative pore volume fraction', fontsize=12)\n",
    "\n",
    "# Microbial domain shading and annotation\n",
    "x_lo = max(MICROBIAL_LO, float(diameters.min()))\n",
    "x_hi = min(MICROBIAL_HI, float(diameters.max()))\n",
    "if x_lo < x_hi:\n",
    "    ax1.axvspan(x_lo, x_hi, alpha=0.08, color='orange', zorder=0)\n",
    "    ax1.axvline(x_lo, color='orange', linestyle='--', linewidth=1.2, alpha=0.8)\n",
    "    ax1.axvline(x_hi, color='orange', linestyle='--', linewidth=1.2, alpha=0.8)\n",
    "    mid_x = float(np.sqrt(x_lo * x_hi))\n",
    "    y_top = float(volume_fraction.max())\n",
    "    ax1.text(mid_x, y_top * 0.95, 'Microbial\\nactive domain',\n",
    "             ha='center', va='top', fontsize=9, color='darkorange',\n",
    "             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',\n",
    "                       edgecolor='orange', alpha=0.85))\n",
    "\n",
    "ax1.set_xlabel('Pore Diameter (\\u00b5m)', fontsize=12)\n",
    "ax1.set_ylabel('Pore volume fraction', fontsize=12)\n",
    "ax1.set_xscale('log')\n",
    "ax1.set_title(f'Pore Size Distribution \\u2014 {latest.name}', fontsize=13, fontweight='bold')\n",
    "ax1.grid(True, which='both', alpha=0.3)\n",
    "\n",
    "h1, l1 = ax1.get_legend_handles_labels()\n",
    "h2, l2 = ax2.get_legend_handles_labels()\n",
    "ax1.legend(h1 + h2, l1 + l2, loc='upper right', fontsize=10)\n",
    "\n",
    "out_path = latest / 'psd_30bins_microbial_active_domain.png'\n",
    "fig.savefig(str(out_path), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print(f'Saved: {out_path}')\n",
]

# ── Cell 19 (id=ac07e715): Step 9 markdown ──────────────────────────────────
STEP9_MD = [
    "## Step 9 — Supplementary Diagnostic Plots\n",
    "\n",
    "Displays the two extra plots generated automatically by the pipeline:\n",
    "\n",
    "* **psd_30bins_microbial_active_domain.png** — pore volume fraction per bin\n",
    "  (30 log-spaced bins, full diameter range), cumulative on right axis,\n",
    "  30–150 µm microbial active domain highlighted\n",
    "* **psd_kde.png** — KDE-smoothed diameter distribution (log-space Scott bandwidth,\n",
    "  Jacobian-corrected to µm)\n",
]

# ── Cell 20 (id=a3c5da0a): Step 9 code ──────────────────────────────────────
STEP9_CODE = [
    "from pathlib import Path\n",
    "import matplotlib.pyplot as plt\n",
    "import matplotlib.image as mpimg\n",
    "\n",
    "run_folders = sorted(Path(OUTPUT_ROOT).glob('psd_diag_*'))\n",
    "if not run_folders:\n",
    "    raise FileNotFoundError(f'No run folders found in {OUTPUT_ROOT}')\n",
    "latest = run_folders[-1]\n",
    "\n",
    "main_path = latest / 'psd_30bins_microbial_active_domain.png'\n",
    "kde_path  = latest / 'psd_kde.png'\n",
    "\n",
    "missing = [p for p in (main_path, kde_path) if not p.exists()]\n",
    "if missing:\n",
    "    print('WARNING: plot file(s) not found:', [p.name for p in missing])\n",
    "    print('Re-run Step 5 / 6 to regenerate outputs with the updated pipeline.')\n",
    "else:\n",
    "    fig, axes = plt.subplots(1, 2, figsize=(16, 5))\n",
    "    for ax, path in zip(axes, (main_path, kde_path)):\n",
    "        ax.imshow(mpimg.imread(str(path)))\n",
    "        ax.axis('off')\n",
    "        ax.set_title(path.name, fontsize=11)\n",
    "    fig.suptitle(f'Supplementary plots \\u2014 {latest.name}', fontsize=13)\n",
    "    plt.tight_layout()\n",
    "    plt.show()\n",
]

# ── Apply patches ────────────────────────────────────────────────────────────
CELL_MAP = {
    'fedf8ac1': STEP8_MD,
    'dda05dc5': STEP8_CODE,
    'ac07e715': STEP9_MD,
    'a3c5da0a': STEP9_CODE,
}

patched = 0
for cell in nb['cells']:
    cid = cell.get('id', '')
    if cid in CELL_MAP:
        cell['source'] = CELL_MAP[cid]
        patched += 1
        print(f'  Patched cell {cid} ({cell["cell_type"]})')

print(f'\nPatched {patched}/4 cells.')

with NB_PATH.open('w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f'Written: {NB_PATH}')
