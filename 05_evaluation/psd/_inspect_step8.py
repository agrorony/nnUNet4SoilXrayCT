import json, pathlib

nb = json.loads(pathlib.Path("colab_psd_diagnostics.ipynb").read_text(encoding="utf-8"))
target = "dda05dc5"
for i, cell in enumerate(nb["cells"]):
    if cell.get("id", "") == target:
        print(f"--- cell {i} id={target} ---")
        print("".join(cell["source"]))
