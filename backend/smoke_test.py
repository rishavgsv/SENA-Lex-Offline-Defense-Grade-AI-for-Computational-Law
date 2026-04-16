"""
Smoke test: embedding + LLM generation via Ollama
"""
import requests
import json
import sys

BASE = "http://localhost:11434"

# --- Test 1: Embedding ---
print("=" * 50)
print("TEST 1: nomic-embed-text embedding")
r = requests.post(f"{BASE}/api/embeddings", json={"model": "nomic-embed-text", "prompt": "What is the penalty clause?"})
if r.status_code == 200:
    vec = r.json()["embedding"]
    print(f"  OK — vector dim: {len(vec)}")
else:
    print(f"  FAILED: {r.status_code} {r.text}")
    sys.exit(1)

# --- Test 2: LLM generation ---
print("\nTEST 2: sena-lex-mistral generation")
context = "Section 12(b): The party in breach shall pay liquidated damages of Rs. 50,000 per day of delay."
prompt = f"""Using the following legal document context, answer the question precisely.
Cite sources as (Document Name, Page X). If the answer is not present, say 'Answer not found.'

Context:
{context}

Question: What is the penalty for breach?

Answer:"""

r = requests.post(
    f"{BASE}/api/generate",
    json={"model": "sena-lex-mistral", "prompt": prompt, "stream": False,
          "options": {"temperature": 0.1, "num_predict": 150}},
    timeout=120
)
if r.status_code == 200:
    answer = r.json().get("response", "")
    print(f"  OK — Answer: {answer.strip()[:200]}")
else:
    print(f"  FAILED: {r.status_code} {r.text}")

print("\n" + "=" * 50)
print("All smoke tests passed! Backend is ready.")
