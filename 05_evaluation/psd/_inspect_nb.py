import json
with open(r'c:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\analysis\colab_psd_diagnostics.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
for i, cell in enumerate(nb['cells']):
    src = ''.join(cell['source'])
    if 'Step 8' in src or 'Step 9' in src or 'psd_20bins' in src or 'unreliable' in src:
        cell_id = cell.get('id', '??')
        cell_type = cell['cell_type']
        print(f'=== Cell {i+1} id={cell_id} type={cell_type} ===')
        print(src[:3000])
        print()
