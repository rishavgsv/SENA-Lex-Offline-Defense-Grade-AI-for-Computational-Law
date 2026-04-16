from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .schemas import QueryRequest, QueryResponse, IngestResponse, SourceCitation, SystemStatus, DocumentActionRequest
import json
from .ingest import get_chunks_from_bytes
from .vector_store import VectorStore
from .llm import LocalLLM
from .graph_engine import graph_engine
from .confidence_engine import ConfidenceEngine
import logging

app = FastAPI(title="SENA-Lex API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vstore = VectorStore()
llm = None
confidence_engine = None

@app.on_event("startup")
async def startup_event():
    global llm, confidence_engine
    logging.info("Connecting to Ollama LLM backend...")
    llm = LocalLLM()
    confidence_engine = ConfidenceEngine(embed_fn=vstore.embed_text)
    logging.info("Confidence Engine v2 initialized.")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend operational"}

@app.get("/api/status", response_model=SystemStatus)
def get_status():
    global llm
    total_docs = len(set(c["document"] for c in vstore.metadata))
    total_chunks = len(vstore.metadata)
    ollama_ok = llm is not None
    return {
        "status": "online",
        "ollama_connected": ollama_ok,
        "model_loaded": ollama_ok,
        "total_documents": total_docs,
        "total_chunks": total_chunks
    }

@app.get("/api/documents")
def get_documents():
    docs = {}
    for c in vstore.metadata:
        doc_name = c.get("document", "Unknown")
        docs[doc_name] = docs.get(doc_name, 0) + 1
    return [{"id": name, "name": name, "chunks": count, "status": "ready"} for name, count in docs.items()]

@app.post("/api/documents/delete")
async def delete_document(request: DocumentActionRequest):
    filename = request.filename
    removed = vstore.remove_document(filename)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
    # Also clean up from knowledge graph
    try:
        nodes_to_remove = [n for n in graph_engine.graph.nodes if n.startswith(f"{filename}::") or n == filename]
        graph_engine.graph.remove_nodes_from(nodes_to_remove)
    except Exception as e:
        logging.warning(f"Could not clean knowledge graph for '{filename}': {e}")
    logging.info(f"Deleted document '{filename}' ({removed} chunks removed).")
    return {"filename": filename, "chunks_removed": removed, "status": "deleted"}

indexing_tasks = set()
indexing_progress = {}

def process_upload_background(chunks, filename):
    indexing_tasks.add(filename)
    indexing_progress[filename] = {"current": 0, "total": len(chunks)}
    
    def progress_cb(current, total):
        indexing_progress[filename] = {"current": current, "total": total}

    try:
        vstore.add_chunks(chunks, progress_cb)
        graph_engine.build_from_chunks(chunks)
        logging.info(f"Background indexing complete for '{filename}' ({len(chunks)} clauses).")
    except Exception as e:
        logging.error(f"Background indexing failed for '{filename}': {e}")
    finally:
        indexing_tasks.discard(filename)
        if filename in indexing_progress:
            del indexing_progress[filename]

@app.get("/api/documents/progress")
async def get_documents_progress():
    return indexing_progress

@app.post("/api/upload", response_model=IngestResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    allowed = {"pdf", "txt", "docx"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '.{ext}'. Please upload a PDF, TXT, or DOCX file."
        )
    try:
        contents = await file.read()
        chunks = get_chunks_from_bytes(contents, file.filename)
    except Exception as e:
        logging.exception(f"Failed to parse '{file.filename}': {e}")
        raise HTTPException(status_code=422, detail=f"Could not parse file: {str(e)}")

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from this file. It may be scanned/image-only or empty."
        )

    background_tasks.add_task(process_upload_background, chunks, file.filename)
    logging.info(f"Queued '{file.filename}' for background indexing.")
    return {"filename": file.filename, "chunks_indexed": len(chunks), "status": "processing_in_background"}

@app.post("/api/query")
async def query_model(request: QueryRequest):
    mode = request.response_mode or "detailed"
    top_k_map = {"brief": 3, "detailed": 5, "comprehensive": 8}
    top_k = top_k_map.get(mode, 5)
    top_chunks = vstore.search(request.query, top_k=top_k, document_filter=request.document_filter)
    
    sources = []
    for c in top_chunks:
        sources.append({
            "document": c.get("document", "Unknown"),
            "page": c.get("page_no", 0),
            "paragraph": c.get("paragraph_id", 0),
            "text_snippet": c.get("text", "")
        })

    if not top_chunks:
        empty_breakdown = {
            "retrieval_relevance": 0, "answer_faithfulness": 0,
            "cross_chunk_agreement": 0, "citation_coverage": 0,
            "query_coverage": 0, "final_score": 0
        }
        async def empty_stream():
            yield f"data: {json.dumps({'confidence': 0.0, 'sources': [], 'confidence_breakdown': empty_breakdown})}\n\n"
            yield f"data: {json.dumps({'text': 'Answer not found in provided documents.'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")
        
    global llm, confidence_engine
    if llm and hasattr(llm, 'stream_generate_answer'):
        async def stream_generator():
            # Send sources immediately (confidence will be sent after generation)
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            # Stream answer and collect full text
            full_answer = ""
            for chunk in llm.stream_generate_answer(request.query, top_chunks, request.chat_history, response_mode=mode):
                yield chunk
                # Extract text from SSE chunk to build full answer
                if chunk.startswith("data: "):
                    try:
                        data = json.loads(chunk[5:].strip())
                        if "text" in data:
                            full_answer += data["text"]
                    except Exception:
                        pass
            
            # Run confidence engine on the completed answer
            if confidence_engine and full_answer.strip():
                try:
                    breakdown = confidence_engine.evaluate(
                        request.query, full_answer, top_chunks
                    )
                    yield f"data: {json.dumps({'confidence': breakdown['final_score'], 'confidence_breakdown': breakdown})}\n\n"
                except Exception as e:
                    logging.error(f"Confidence engine error: {e}")
                    # Fallback to simple average
                    avg = sum(c.get('similarity_score', 0) for c in top_chunks) / len(top_chunks)
                    yield f"data: {json.dumps({'confidence': round(avg, 2)})}\n\n"
            else:
                avg = sum(c.get('similarity_score', 0) for c in top_chunks) / len(top_chunks)
                yield f"data: {json.dumps({'confidence': round(avg, 2)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        async def mock_stream():
            mock_answer = f"[MOCK GENERATION] The model is not loaded. Based on semantics: found {len(top_chunks)} related chunks."
            # Even mock gets a confidence breakdown
            if confidence_engine:
                breakdown = confidence_engine.evaluate(request.query, mock_answer, top_chunks)
                yield f"data: {json.dumps({'confidence': breakdown['final_score'], 'sources': sources, 'confidence_breakdown': breakdown})}\n\n"
            else:
                avg = sum(c.get('similarity_score', 0) for c in top_chunks) / len(top_chunks)
                yield f"data: {json.dumps({'confidence': round(avg, 2), 'sources': sources})}\n\n"
            yield f"data: {json.dumps({'text': mock_answer})}\n\n"
        return StreamingResponse(mock_stream(), media_type="text/event-stream")

@app.post("/api/summarize")
async def summarize_document(request: DocumentActionRequest):
    chunks = [c for c in vstore.metadata if c.get("document") == request.filename]
    if not chunks:
        async def empty_stream():
            if request.filename in indexing_tasks:
                yield f"data: {json.dumps({'text': 'Document is still being indexed in the background. Please wait a few moments...'})}\n\n"
            else:
                yield f"data: {json.dumps({'text': 'Document not found or has no text.'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")
        
    global llm
    if llm and hasattr(llm, 'analyze_document'):
        return StreamingResponse(
            llm.analyze_document("Provide a concised, 3-sentence summary of this document's primary purpose and key terms.", chunks),
            media_type="text/event-stream"
        )
    async def mock_stream():
        yield f"data: {json.dumps({'text': '[MOCK GENERATION] Summary not available because model is offline.'})}\n\n"
    return StreamingResponse(mock_stream(), media_type="text/event-stream")


class CompareRequest(BaseModel):
    document_1: str
    document_2: str

@app.post("/api/clauses/compare")
async def compare_clauses(request: CompareRequest):
    chunks1 = [c for c in vstore.metadata if c.get("document") == request.document_1]
    chunks2 = [c for c in vstore.metadata if c.get("document") == request.document_2]
    
    if not chunks1 or not chunks2:
         async def empty_stream():
             yield f"data: {json.dumps({'text': 'Cannot compare: One or both documents missing.'})}\n\n"
         return StreamingResponse(empty_stream(), media_type="text/event-stream")
         
    global llm
    if llm and hasattr(llm, 'analyze_document'):
        # Merge top 7 chunks from doc1 and top 8 chunks from doc2
        combined_chunks = chunks1[:7] + chunks2[:8]
        task = f"Perform a differential analysis comparing the obligations and liabilities between Document 1 ({request.document_1}) and Document 2 ({request.document_2}). Highlight any contradictions or differences in terms."
        return StreamingResponse(
            llm.analyze_document(task, combined_chunks),
            media_type="text/event-stream"
        )
    
    async def mock_stream():
        yield f"data: {json.dumps({'text': '[MOCK GENERATION] Compare endpoint is offline.'})}\n\n"
    return StreamingResponse(mock_stream(), media_type="text/event-stream")


@app.post("/api/detect-violations")
async def detect_violations(request: DocumentActionRequest):
    chunks = [c for c in vstore.metadata if c.get("document") == request.filename]
    if not chunks:
        async def empty_stream():
            if request.filename in indexing_tasks:
                yield f"data: {json.dumps({'text': 'Document is still being indexed in the background. Please wait a few moments...'})}\n\n"
            else:
                yield f"data: {json.dumps({'text': 'Document not found or has no text.'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    global llm
    if llm and hasattr(llm, 'analyze_document'):
        
        # Semantic Pre-Filtering: Interrogate FAISS for the highest-likelihood punitive clauses mathematically.
        risk_query = "liability, penalty, termination, termination fee, dispute resolution, indemnification, breach of contract, damages, governing law, arbitration, punitive, risk"
        top_risk_chunks = vstore.search(risk_query, top_k=15, document_filter=request.filename)
        
        eval_chunks = top_risk_chunks if top_risk_chunks else chunks

        task = """Analyze this document for legal risks, non-compliance issues, punitive clauses, or unusual liabilities.
You MUST output a valid JSON Object containing a single key "violations" which holds an array of risks. Do not include markdown or explanations.
Example format:
{
  "violations": [
    {
      "clause_id": "Section X",
      "text_snippet": "exact quote from text",
      "risk_level": "High",
      "reason": "Why this is a risk",
      "page_no": 1
    }
  ]
}"""
        return StreamingResponse(
            llm.analyze_document(task, eval_chunks, json_mode=True),
            media_type="text/event-stream"
        )
    async def mock_stream():
        # Mock semantic Risk Array
        mock_array = [
            {
                "clause_id": "General",
                "text_snippet": "the defendant claims that under the section 4A, there is a liability exception",
                "risk_level": "High",
                "reason": "Liability exception without bounds",
                "page_no": 1
            }
        ]
        yield f"data: {json.dumps({'text': json.dumps(mock_array)})}\n\n"
    return StreamingResponse(mock_stream(), media_type="text/event-stream")
