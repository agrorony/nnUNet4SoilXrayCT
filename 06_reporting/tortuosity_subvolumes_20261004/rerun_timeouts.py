"""Sensitivity: re-solve the 175 s timeouts with a 900 s limit (same function/settings). Reported separately."""
import pandas as pd
from run_tortuosity_subvolumes import run_tasks, HERE
if __name__ == "__main__":
    d = pd.read_csv(HERE/"work/raw_full_s200.csv"); t = d[d.status == "timeout"]
    tasks = [dict(key=(r.specimen, r.cube_index, r.axis), cube_file=str(HERE/"work/cubes"/f"{r.specimen}_s200_c{r.cube_index}.npy"), axis=int(r.axis), phase="original") for r in t.itertuples()]
    res = run_tasks(tasks, 900, 5)
    out = pd.DataFrame([dict(specimen=k[0], cube_index=k[1], axis=k[2], status=v[0], tortuosity=v[1], runtime_s=v[2], message=v[3]) for k, v in res.items()])
    out.to_csv(HERE/"work/timeout_rerun_900s.csv", index=False); print(out.to_string())
