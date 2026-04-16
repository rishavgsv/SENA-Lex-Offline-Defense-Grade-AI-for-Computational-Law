import requests
import json
import sys

model_name = "sena-lex-mistral"
gguf_path = r"C:\Users\Risha\OneDrive\Documents\Desktop\NLP Project\backend\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf"

payload = {
    "name": model_name,
    "from": gguf_path,
    "system": (
        "You are a formal, precise legal assistant. "
        "Answer ONLY using the provided context. "
        "If the answer is not present in the context, respond exactly with: "
        "'Answer not found in provided documents.' "
        "Do NOT add any information from outside the context. Do NOT speculate or hallucinate."
    ),
    "parameters": {
        "temperature": 0.1,
        "top_p": 0.9,
        "num_ctx": 4096,
    }
}

print(f"Importing '{model_name}' from local GGUF...")
print(f"Path: {gguf_path}")
print("---")

response = requests.post(
    "http://localhost:11434/api/create",
    json=payload,
    stream=True,
    timeout=600
)

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        status = data.get("status", "")
        err = data.get("error", "")
        if err:
            print(f"ERROR: {err}")
            sys.exit(1)
        if status:
            print(f"  {status}")

print(f"\nModel '{model_name}' ready in Ollama!")
