import numpy as np, json, os
e = np.load('data/embeddings.npy')
d = json.load(open('data/metadata.json', 'r', encoding='utf-8'))
m = d.get('metadata', [])
dim_in_json = d.get('dim')
print(f'embeddings.npy : {len(e)} vectors, dim={e.shape[1]}')
print(f'metadata       : {len(m)} chunks')
print(f'dim in JSON    : {dim_in_json}')
match = len(e) == len(m)
print(f'MATCH          : {match}')
if match:
    print('\nAll good — delete will use the fast slice path on next startup.')
else:
    print('\nMISMATCH — run rebuild_cache.py again.')
