PY=/c/Users/rony.schwartz/venv-render3d/Scripts/python.exe
cd "$(dirname "$0")"
for v in full close; do echo "== opt 3 $v"; $PY render.py 3 full $v 3000 ../renders 2>&1 | tail -3; done
echo ALLDONE
