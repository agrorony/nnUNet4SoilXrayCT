# Re-render the Mishmar set with the updated render.py (true close-up size label, box dimensions, POM smoothing in close-ups, raw frames saved)
PY=/c/Users/rony.schwartz/venv-render3d/Scripts/python.exe
cd "$(dirname "$0")"
for o in 2 3 1; do for v in full close; do echo "== opt $o $v"; $PY render.py $o full $v 3000 ../renders 2>&1 | tail -3; done; done
echo ALLDONE
