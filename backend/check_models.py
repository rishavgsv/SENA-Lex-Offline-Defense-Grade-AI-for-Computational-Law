import requests

r = requests.get("http://localhost:11434/api/tags")
models = r.json().get("models", [])
print("Available Ollama models:")
for m in models:
    size_gb = round(m["size"] / 1e9, 2)
    print(f"  - {m['name']} ({size_gb} GB)")
