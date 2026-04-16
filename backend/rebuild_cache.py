"""One-time script to extract embeddings from existing FAISS index and save as embeddings.npy cache.
This allows instant document deletion without re-embedding."""

import faiss
import numpy as np
import os
import json

DATA_DIR = "data"
index_path = os.path.join(DATA_DIR, "index.faiss")
meta_path = os.path.join(DATA_DIR, "metadata.json")
embeddings_path = os.path.join(DATA_DIR, "embeddings.npy")

if not os.path.exists(index_path):
    print("No FAISS index found. Nothing to do.")
    exit(0)

if os.path.exists(embeddings_path):
    print("embeddings.npy already exists. Skipping.")
    exit(0)

# Load index and extract all vectors
index = faiss.read_index(index_path)
n = index.ntotal
dim = index.d
print(f"FAISS index: {n} vectors, dimension {dim}")

# Reconstruct all vectors from the index
embeddings = np.zeros((n, dim), dtype="float32")
for i in range(n):
    embeddings[i] = index.reconstruct(i)

np.save(embeddings_path, embeddings)
print(f"Saved {n} embeddings to {embeddings_path} ({os.path.getsize(embeddings_path) / 1024 / 1024:.1f} MB)")
