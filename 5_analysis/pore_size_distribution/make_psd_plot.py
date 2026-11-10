import csv, pathlib, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def make_psd_plot(csv_path, title_suffix=""):
    csv_path = pathlib.Path(csv_path)
    run_dir = csv_path.parent
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"d": float(r["Diameter_um"]), "v": float(r["Differential_PSD"])})
    in_range = [r for r in rows if 30.0 <= r["d"] <= 150.0]
    if not in_range:
        print(f"WARNING: no data in 30-150 um for {run_dir.name}")
        return
    diams = np.array([r["d"] for r in in_range])
    diffs = np.array([r["v"] for r in in_range])
    bin_edges = np.linspace(30.0, 150.0, 21)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_vals = np.zeros(20)
    for i in range(20):
        mask = (diams >= bin_edges[i]) & (diams < bin_edges[i+1])
        if mask.any():
            bin_vals[i] = diffs[mask].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(bin_centers, bin_vals, width=(bin_edges[1]-bin_edges[0])*0.85,
           color="steelblue", edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Pore Diameter (um)", fontsize=12)
    ax.set_ylabel("Differential PSD", fontsize=12)
    ax.set_xlim(30, 150)
    label = title_suffix or run_dir.name
    ax.set_title(f"Pore Size Distribution (20 bins, 30-150 um)\n{label}", fontsize=13)
    ax.tick_params(axis="both", labelsize=10)
    plt.tight_layout()
    out = run_dir / "psd_20bins_30_150um.png"
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")

if __name__ == "__main__":
    make_psd_plot(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
