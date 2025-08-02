from fastapi import Depends, FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any
import uuid
import asyncio
import itertools
from unstructured.partition.auto import partition
from tenacity import retry, stop_after_attempt, wait_random_exponential

# --- Correct Environment Variable Loading ---
ROOT_DIR = Path(__file__).parent
dotenv_path = ROOT_DIR / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)

# --- API Key Rotation Setup ---
api_keys_str = os.environ.get("GOOGLE_API_KEYS", "")
api_keys_list = [key.strip() for key in api_keys_str.split(',') if key.strip()]
if not api_keys_list:
    raise ValueError("CRITICAL ERROR: GOOGLE_API_KEYS not found in .env file.")
key_cycler = itertools.cycle(api_keys_list)
def get_next_api_key():
    return next(key_cycler)

# --- MongoDB Connection ---
mongo_url = os.environ.get('MONGO_URL', "mongodb://localhost:27017")
db_name = os.environ.get('DB_NAME', "aura_database")
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# --- FastAPI App Initialization ---
app = FastAPI(title="Aura Intelligent Retrieval Engine", version="1.0.0")
api_router = APIRouter(prefix="/api")

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    documents: HttpUrl
    questions: List[str] = Field(..., min_items=1, max_items=50)

class QueryResponse(BaseModel):
    answers: List[str]
    metadata: Dict[str, Any]
    processing_time: float
    request_id: str

# --- Authentication ---
security = HTTPBearer()
async def verify_bearer_token(credentials = Depends(security)):
    secret_token = os.environ.get("BEARER_TOKEN")
    if not secret_token: raise HTTPException(500, "BEARER_TOKEN not configured.")
    if credentials.credentials != secret_token: raise HTTPException(403, "Invalid token.")
    return credentials

# --- Helper Functions ---
@retry(wait=wait_random_exponential(max=5), stop=stop_after_attempt(3))
async def download_document(url: str) -> bytes:
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content

def extract_text_with_unstructured(pdf_content: bytes) -> str:
    """Reliably extracts structured text and tables using the unstructured library."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
        tf.write(pdf_content)
        temp_file_path = tf.name
    try:
        elements = partition(filename=temp_file_path, strategy="hi_res")
        return "\n\n".join([str(el) for el in elements])
    finally:
        os.unlink(temp_file_path)

@retry(wait=wait_random_exponential(max=10), stop=stop_after_attempt(3))
async def answer_questions_from_context(questions: List[str], context: str) -> List[str]:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    q_block = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    prompt = f"""**ROLE:** You are an AI Documentation Auditor.
**TASK:** Provide a detailed and complete answer for every question below, based ONLY on the provided DOCUMENT CONTEXT.
**CRITICAL RULES:**
1. **Be Thorough:** Your primary goal is accuracy. Scan the entire document context. Failure to find an answer is a critical error.
2. **Clean Output:** Your response MUST ONLY contain the answers. Do NOT repeat questions, use numbering, or add intros.
3. **Separator:** You MUST separate each answer with '---ANSWER---'.
4. **Missing Data:** If an answer is not in the document, respond with: "The answer to this question could not be found in the document."

**DOCUMENT CONTEXT:**
---
{context}
---
**QUESTIONS TO ANSWER:**
{q_block}
"""
    chat = LlmChat(api_key=get_next_api_key(), session_id=str(uuid.uuid4()), system_message="You are a document analysis AI.").with_model("gemini", "gemini-2.0-flash")
    msg = UserMessage(text=prompt)
    resp = await chat.send_message(msg)
    answers = [a.strip() for a in resp.split('---ANSWER---')]
    if len(answers) < len(questions):
        answers.extend(["Error: AI response malformed or incomplete."] * (len(questions) - len(answers)))
    return answers[:len(questions)]

# --- API Endpoints ---
@api_router.get("/health")
async def health_check():
    return {"status": "healthy" if api_keys_list else "unhealthy"}

@api_ōuter.post("/hackrx/run", response_model=QueryResponse, dependencies=[Depends(verify_bearer_token)])
async def process_document_and_wait(request: QueryRequest):
    start_time = asyncio.get_event_loop().time()
    try:
        content = await download_document(str(request.documents))
        
        # New, reliable text extraction that understands tables
        context = extract_text_with_unstructured(content)
        
        answers = await answer_questions_from_context(request.questions, context)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        return QueryResponse(
            answers=answers,
            metadata={"document_name": Path(str(request.documents)).name.split('?')[0]},
            processing_time=processing_time,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        logging.error(f"Request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {e}")

# --- Final App Setup ---
app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')