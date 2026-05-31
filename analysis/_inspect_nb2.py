import json
with open(r'c:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\analysis\colab_psd_diagnostics.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
for i, cell in enumerate(nb['cells'][18:23], start=19):
    src = ''.join(cell['source'])
    cell_id = cell['id']
    cell_type = cell['cell_type']
    print(f'--- Cell {i} id={cell_id} type={cell_type} ---')
    print(src[:2000])
    print()
