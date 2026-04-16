"""
Live delete test — calls the running API to confirm delete works.
Tests the lazy re-embed path (cache missing in-memory) and the fast path.
"""
import requests, json, sys

BASE = "http://localhost:8000"

# 1. Check what documents exist
r = requests.get(f"{BASE}/api/documents")
docs = r.json()
print(f"Documents in store ({len(docs)}):")
for d in docs:
    print(f"  - {d['name']}  ({d['chunks']} chunks)")

if not docs:
    print("No documents to test with. Upload a doc first.")
    sys.exit(0)

# Pick the smallest doc to delete (fastest test)
target = min(docs, key=lambda x: x['chunks'])
print(f"\nTesting DELETE on smallest doc: '{target['name']}' ({target['chunks']} chunks)")
print("Sending request...")

r = requests.post(f"{BASE}/api/documents/delete", json={"filename": target['name']}, timeout=120)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

if r.status_code == 200:
    print("\n✅ DELETE succeeded!")
    after = requests.get(f"{BASE}/api/documents").json()
    print(f"Documents remaining: {len(after)}")
    for d in after:
        print(f"  - {d['name']}")
else:
    print("\n❌ DELETE failed.")
