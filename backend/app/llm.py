import requests
import logging
import json
from typing import List, Dict

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "sena-lex-mistral"

class LocalLLM:
    def __init__(self):
        self.model = MODEL_NAME
        self._check_ollama()

    def _check_ollama(self):
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                # Strip :latest tag for comparison
                models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
                if self.model not in models:
                    logging.warning(
                        f"Model '{self.model}' not found in Ollama. "
                        f"Available: {models}. "
                        f"Run: ollama create {self.model} -f Modelfile"
                    )
                else:
                    logging.info(f"Ollama model '{self.model}' ready.")
        except Exception as e:
            logging.warning(f"Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}. LLM will be mocked.")

    def decompose_query(self, query: str) -> List[str]:
        """Splits a complex user query into 1-3 simpler sub-queries for multi-hop reasoning."""
        prompt = f"Decompose this complex legal query into 1-3 distinct, simple sub-queries. Output ONLY a numbered list.\nQuery: {query}\nSub-queries:"
        try:
             response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 128}},
                timeout=30
            )
             if response.status_code == 200:
                 res = response.json().get("response", "").strip()
                 subqueries = [r.strip() for r in res.split("\n") if r.strip() and r[0].isdigit()]
                 return subqueries if subqueries else [query]
        except Exception as e:
             logging.error(f"Decomposition failed: {e}")
        return [query]

    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        # Step 1: Decompose query (could be utilized later to query vector store multiple times)
        sub_queries = self.decompose_query(query)
        logging.info(f"Decomposed queries: {sub_queries}")
        
        context_text = "\n\n".join(
            [f"[Source {i+1} | {c.get('document','?')} | Page {c.get('page_no','?')}]\n{c.get('text','')}"
             for i, c in enumerate(context_chunks)]
        )

        prompt = f"""Using the following legal document context, answer the question precisely.
Cite sources as (Document Name, Page X). If the answer is not present, say "Answer not found in provided documents."

Context:
{context_text}

Question: {query}

Answer:"""

        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 512,
                    }
                },
                timeout=120
            )
            if response.status_code == 200:
                draft = response.json().get("response", "").strip()
                
                # Step 2: Strict Validation
                verify_prompt = f"""You are a strict defense-grade legal auditor.
Review the following drafted answer against the provided document excerpts.
If the drafting answer contains a claim, entity, or date NOT present in the Document Context, output strictly: "INVALID: Hallucination detected."
If the answer is completely supported by the text, output strictly: "VALID: Anti-Hallucination check passed."

Document Context:
{context_text}

Drafted Answer:
{draft}

Verification Status:"""
                v_response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": self.model, "prompt": verify_prompt, "stream": False, "options": {"temperature": 0.0, "num_predict": 64}},
                    timeout=30
                )
                if v_response.status_code == 200:
                    status = v_response.json().get("response", "").strip()
                    return f"{draft}\n\n[Verification Trace]: {status}"
                    
                return draft
            else:
                logging.error(f"Ollama error {response.status_code}: {response.text}")
                return "Error: LLM returned an unexpected response."
        except requests.exceptions.ConnectionError:
            return "[Offline] Cannot reach local Ollama server. Please ensure Ollama is running."
        except Exception as e:
            logging.error(f"LLM generation failed: {e}")
            return f"Error during generation: {str(e)}"

    def stream_generate_answer(self, query: str, context_chunks: List[Dict], chat_history: List[Dict] = [], response_mode: str = "detailed"):
        context_text = "\n\n".join(
            [f"[Source {i+1} | {c.get('document','?')} | Page {c.get('page_no','?')}]\n{c.get('text','')}"
             for i, c in enumerate(context_chunks)]
        )

        history_text = ""
        if chat_history:
            history_text = "Previous Conversation:\n"
            for msg in chat_history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content')}\n"
            history_text += "\n"

        # Mode-specific prompt and token limits
        mode_config = {
            "brief": {
                "instruction": "Answer in 2-3 concise sentences. Be direct and to the point. Cite only the single most relevant source.",
                "num_predict": 256,
                "temperature": 0.1,
            },
            "detailed": {
                "instruction": "Answer precisely with moderate detail. Cite sources as (Document Name, Page X). If the answer is not present, say \"Answer not found in provided documents.\"",
                "num_predict": 512,
                "temperature": 0.1,
            },
            "comprehensive": {
                "instruction": "Provide an exhaustive, multi-paragraph analysis covering all relevant aspects found in the context. Include every applicable source citation as (Document Name, Page X). Discuss nuances, exceptions, and related provisions. Structure your answer with clear sections if appropriate.",
                "num_predict": 1024,
                "temperature": 0.15,
            },
        }
        config = mode_config.get(response_mode, mode_config["detailed"])

        prompt = f"""Using the following legal document context, {config['instruction']}

{history_text}Context:
{context_text}

Question: {query}

Answer:"""

        try:
            with requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": config["temperature"],
                        "top_p": 0.9,
                        "num_predict": config["num_predict"],
                    }
                },
                stream=True,
                timeout=120
            ) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'LLM returned an unexpected response'})}\n\n"
                    return

                draft = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        text = chunk.get("response", "")
                        draft += text
                        # Yield in Server-Sent Events (SSE) format
                        yield f"data: {json.dumps({'text': text})}\n\n"

                # Trigger Verification Trace
                trace_msg = json.dumps({'text': '\n\n**[Running Verification Trace...]**\n'})
                yield f"data: {trace_msg}\n\n"
                verify_prompt = f"""You are a strict defense-grade legal auditor.
Review the following drafted answer against the document context.
If it contains a claim, entity, or date NOT present in the Context, output strictly: "❌ INVALID: Hallucination detected. Unverified claims found."
If the answer is completely supported, output strictly: "✅ VALID: Anti-Hallucination check passed."

Context:
{context_text}

Drafted Answer:
{draft}

Status:"""
                with requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": self.model, "prompt": verify_prompt, "stream": True, "options": {"temperature": 0.0, "num_predict": 128}},
                    stream=True, timeout=120
                ) as v_response:
                    if v_response.status_code == 200:
                         for line in v_response.iter_lines():
                             if line:
                                 chunk = json.loads(line)
                                 yield f"data: {json.dumps({'text': chunk.get('response', '')})}\n\n"
                        
        except requests.exceptions.ConnectionError:
            yield f"data: {json.dumps({'text': '[Offline] Cannot reach local Ollama server.'})}\n\n"
        except Exception as e:
            logging.error(f"LLM streaming failed: {e}")
            err_msg = json.dumps({'text': f'Error during generation: {str(e)}'})
            yield f"data: {err_msg}\n\n"

    def analyze_document(self, task: str, context_chunks: List[Dict], json_mode: bool = False):
        # Limit to top 15 chunks to avoid context window explosion
        context_text = "\n\n".join([f"[Page {c.get('page_no','?')}] {c.get('text','')}" for c in context_chunks[:15]])

        prompt = f"""You are SENA-Lex, a highly critical and precise defense-grade legal AI.
Based strictly on the following document excerpts, provide the requested analysis. Do not invent information.

Document Excerpts:
{context_text}

Task: {task}
"""

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1024,
                }
            }
            if json_mode:
                payload["format"] = "json"

            with requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                stream=True,
                timeout=120
            ) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'LLM returned an unexpected response'})}\n\n"
                    return

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield f"data: {json.dumps({'text': chunk.get('response', '')})}\n\n"
                        
        except requests.exceptions.ConnectionError:
            yield f"data: {json.dumps({'text': '[Offline] Cannot reach local Ollama server.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'text': f'Error during generation: {str(e)}'})}\n\n"

