"""
Download the sentence-transformers embedding model using urllib (no httpx, HF SDK).
Run this script ONCE before starting the backend.
"""
import urllib.request
import os
import json
import sys

MODEL_DIR = "models/all-MiniLM-L6-v2"
BASE_URL = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"

FILES = [
    "config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "vocab.txt",
    "special_tokens_map.json",
    "sentence_bert_config.json",
    "modules.json",
    "1_Pooling/config.json",
    "pytorch_model.bin",
]

def reporthook(count, block_size, total_size):
    if total_size > 0:
        pct = int(count * block_size * 100 / total_size)
        mb = count * block_size / 1024 / 1024
        total_mb = total_size / 1024 / 1024
        sys.stdout.write(f"\r  {pct}% ({mb:.2f} MB / {total_mb:.2f} MB)   ")
        sys.stdout.flush()

def download_file(filename):
    url = f"{BASE_URL}/{filename}"
    dest = os.path.join(MODEL_DIR, filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        print(f"  Already exists: {filename}")
        return
    print(f"Downloading {filename} ...")
    try:
        urllib.request.urlretrieve(url, dest, reporthook)
        print()
    except Exception as e:
        print(f"\n  FAILED: {e}")

if __name__ == "__main__":
    print("=== Downloading all-MiniLM-L6-v2 embedding model ===")
    for f in FILES:
        download_file(f)
    print("\nDone. Embedding model saved to:", MODEL_DIR)
