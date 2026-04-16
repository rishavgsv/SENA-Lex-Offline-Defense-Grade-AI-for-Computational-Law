from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"
    chat_history: Optional[List[Dict[str, str]]] = []
    document_filter: Optional[str] = None
    response_mode: Optional[str] = "detailed"  # brief | detailed | comprehensive

class SourceCitation(BaseModel):
    document: str
    page: int
    paragraph: Optional[int] = None
    text_snippet: str

class ConfidenceBreakdown(BaseModel):
    retrieval_relevance: float
    answer_faithfulness: float
    cross_chunk_agreement: float
    citation_coverage: float
    query_coverage: float
    final_score: float

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    sources: List[SourceCitation]

class IngestResponse(BaseModel):
    filename: str
    chunks_indexed: int
    status: str

class SystemStatus(BaseModel):
    status: str
    ollama_connected: bool
    model_loaded: bool
    total_documents: int
    total_chunks: int

class DocumentActionRequest(BaseModel):
    filename: str
