import pickle, os

datasets = [
    'bu04bk04_sc_1812_merged_class.pkl',
    'gy07bu07_1812_merged_class.pkl',
    'br08pk08_1812_merged_class.pkl',
    'ye04gr05_1812_merged_class.pkl',
    'bu04bk04_sc_1812_seg.pkl',
    'gy07bu07_1802_seg.pkl',
    'br08pk08_1812_seg.pkl',
    'ye04gr05_1812_seg.pkl',
]

base = os.path.expanduser('~/.moove/training_data')
for name in datasets:
    path = os.path.join(base, name)
    if not os.path.exists(path):
        print(f'--- {name}: NOT FOUND ---')
        continue
    with open(path, 'rb') as f:
        data = pickle.load(f)
    print(f'=== {name} ===')
    print(f'  Keys: {list(data.keys())}')
    if 'dataframe' in data:
        df = data['dataframe']
        files = sorted(df['file'].unique()) if 'file' in df.columns else ['no file column']
        labels = sorted(df['label'].unique()) if 'label' in df.columns else []
        print(f'  Files ({len(files)}): {files[:5]}...' if len(files)>5 else f'  Files ({len(files)}): {files}')
        print(f'  Labels: {labels}')
        print(f'  Rows: {len(df)}')
    if 'metadata' in data:
        print(f'  Metadata: {data["metadata"]}')
    if 'features' in data:
        import numpy as np
        feat = np.array(data['features'])
        print(f'  Features shape: {feat.shape}')
        if feat.ndim == 2:
            file_ids = np.unique(feat[:, 0])
            print(f'  File indices: {file_ids[:10]}... ({len(file_ids)} unique)')
    if 'syllables' in data:
        print(f'  Syllables: {data["syllables"]}')
    print()