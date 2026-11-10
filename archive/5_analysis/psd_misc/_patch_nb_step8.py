"""Patch notebook cell dda05dc5 (Step 8 code) to re-bin PSD into 30 log-spaced
bins across the full diameter range before plotting."""
import json, pathlib

NB_PATH = pathlib.Path("colab_psd_diagnostics.ipynb")
TARGET_ID = "dda05dc5"

NEW_SOURCE = [
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
    "total_pore_voxels = int(result_data.get('total_pore_voxels', df['Volume_Count'].sum()))\n",
    "\n",
    "# Pipeline bin centers and counts (full resolution from result JSON)\n",
    "bin_centers_um = np.array(result_data.get('bin_centers_um', df['Diameter_um'].values))\n",
    "volume_counts  = np.array(result_data.get('volume_counts',  df['Volume_Count'].values))\n",
    "\n",
    "# ── Re-bin into 30 log-spaced bins across the FULL diameter range ──────────\n",
    "N_BINS   = 30\n",
    "d_min    = float(bin_centers_um.min())\n",
    "d_max    = float(bin_centers_um.max())\n",
    "edges    = np.logspace(np.log10(d_min), np.log10(d_max), N_BINS + 1)\n",
    "centers  = np.sqrt(edges[:-1] * edges[1:])   # geometric mean\n",
    "rebinned, _ = np.histogram(bin_centers_um, bins=edges, weights=volume_counts)\n",
    "\n",
    "volume_fraction    = rebinned / total_pore_voxels\n",
    "cumulative_fraction = np.cumsum(volume_fraction)\n",
    "bar_widths = np.diff(edges)\n",
    "\n",
    "# Microbial active domain bounds\n",
    "MICROBIAL_LO, MICROBIAL_HI = 30.0, 150.0\n",
    "bar_colors = ['#e67300' if MICROBIAL_LO <= d <= MICROBIAL_HI else '#4878cf'\n",
    "               for d in centers]\n",
    "\n",
    "# ── Plot ──────────────────────────────────────────────────────────────────\n",
    "fig, ax1 = plt.subplots(figsize=(11, 6))\n",
    "ax2 = ax1.twinx()\n",
    "\n",
    "ax1.bar(centers, volume_fraction, width=bar_widths,\n",
    "        color=bar_colors, edgecolor='white', linewidth=0.5, alpha=0.85,\n",
    "        label='Pore volume fraction per bin')\n",
    "\n",
    "ax2.plot(centers, cumulative_fraction, color='black', linewidth=2,\n",
    "         label='Cumulative')\n",
    "ax2.set_ylim(0, 1.05)\n",
    "ax2.set_ylabel('Cumulative pore volume fraction', fontsize=12)\n",
    "\n",
    "# Microbial domain shading and annotation\n",
    "x_lo = max(MICROBIAL_LO, d_min)\n",
    "x_hi = min(MICROBIAL_HI, d_max)\n",
    "if x_lo < x_hi:\n",
    "    ax1.axvspan(x_lo, x_hi, alpha=0.10, color='orange', zorder=0)\n",
    "    ax1.axvline(x_lo, color='orange', linestyle='--', linewidth=1.2, alpha=0.8)\n",
    "    ax1.axvline(x_hi, color='orange', linestyle='--', linewidth=1.2, alpha=0.8)\n",
    "    mid_x = float(np.sqrt(x_lo * x_hi))\n",
    "    y_top = float(volume_fraction.max()) if volume_fraction.max() > 0 else 1.0\n",
    "    ax1.text(mid_x, y_top * 0.97, 'Microbial\\nactive domain\\n30\\u2013150 \\u00b5m',\n",
    "             ha='center', va='top', fontsize=9, color='darkorange',\n",
    "             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',\n",
    "                       edgecolor='orange', alpha=0.85))\n",
    "\n",
    "ax1.set_xlabel('Pore Diameter (\\u00b5m)', fontsize=12)\n",
    "ax1.set_ylabel('Pore volume fraction', fontsize=12)\n",
    "ax1.set_xscale('log')\n",
    "ax1.set_title(f'Pore Size Distribution \\u2014 {N_BINS} bins (full range) \\u2014 {latest.name}',\n",
    "              fontsize=13, fontweight='bold')\n",
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

nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
patched = 0
for cell in nb["cells"]:
    if cell.get("id", "") == TARGET_ID:
        cell["source"] = NEW_SOURCE
        patched += 1

if patched == 0:
    print(f"ERROR: cell {TARGET_ID} not found!")
else:
    NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {patched} cell(s). Written: {NB_PATH}")
