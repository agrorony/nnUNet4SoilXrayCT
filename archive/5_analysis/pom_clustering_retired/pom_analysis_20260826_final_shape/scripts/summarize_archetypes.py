import pandas as pd
from pathlib import Path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

df = pd.read_csv(Path(__file__).resolve().parents[1] / "pom_object_features_final.csv")
g = df.groupby("archetype_id")[["elongation", "flatness", "sphericity", "pore_contact_fraction", "diameter_um"]].mean().round(2)
g["n"] = df.groupby("archetype_id").size()
print(g)
