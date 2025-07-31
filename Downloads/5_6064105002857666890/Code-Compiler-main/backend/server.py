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
import mimetypes
import itertools
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
    if not secret_token:
        raise HTTPException(status_code=500, detail="BEARER_TOKEN is not configured.")
    if credentials.credentials != secret_token:
        raise HTTPException(status_code=403, detail="Invalid or missing bearer token.")
    return credentials

# --- Helper Functions ---
@retry(wait=wait_random_exponential(max=5), stop=stop_after_attempt(3))
async def download_document(url: str):
    import httpx
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content

@retry(wait=wait_random_exponential(max=10), stop=stop_after_attempt(3))
async def answer_from_document_directly(content: bytes, filename: str, questions: List[str]) -> List[str]:
    """Sends the PDF and all questions in a single, highly-instructed call."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
    
    q_block = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    # THE FINAL, ULTIMATE PROMPT
    prompt = f"""
    **ROLE:** You are a Digital Documentation Auditor AI.
    **TASK:** Analyze the attached document and provide precise, detailed answers to all questions listed below. Your performance is judged on accuracy and thoroughness.

    **CRITICAL RULES:**
    1.  **Comprehensive Search:** You MUST search the entire document for each answer. Failure to find an answer that is present in the document is a critical error.
    2.  **Strict Context:** Your answers must be based **exclusively** on the text within the attached document. Do not use any external knowledge.
    3.  **Clean Output:** Do NOT repeat the questions, do NOT add introductory text, and do NOT add numbering to your answers.
    4.  **Separator:** You MUST separate each answer from the next using the exact string '---ANSWER---'.
    5.  **Handle Missing Data:** If, and only if, after a complete search you cannot find an answer, you MUST respond with the specific phrase: "After a thorough review, the answer to this question could not be located in the provided document."

    **QUESTIONS TO ANSWER:**
    {q_block}
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tf:
        tf.write(content)
        temp_file_path = tf.name
    try:
        chat = LlmChat(
            api_key=get_next_api_key(), 
            session_id=str(uuid.uuid4()), 
            system_message="You are an AI assistant that follows instructions precisely."
        ).with_model("gemini", "gemini-2.0-flash")
        
        mime, _ = mimetypes.guess_type(filename) or ('application/pdf', None)
        file_attachment = FileContentWithMimeType(file_path=temp_file_path, mime_type=mime)
        
        msg = UserMessage(text=prompt, file_contents=[file_attachment])
        resp = await chat.send_message(msg)
        
        answers = [a.strip() for a in resp.split('---ANSWER---')]
        if len(answers) < len(questions):
            answers.extend(["Error: AI failed to provide a valid response for this question."] * (len(questions) - len(answers)))
        return answers[:len(questions)]
    finally:
        os.unlink(temp_file_path)

# --- API Endpoints ---
@api_router.get("/health")
async def health_check():
    return {"status": "healthy" if api_keys_list else "unhealthy"}

@api_router.post("/hackrx/run", response_model=QueryResponse, dependencies=[Depends(verify_bearer_token)])
async def process_document_and_wait(request: QueryRequest):
    start_time = asyncio.get_event_loop().time()
    try:
        content = await download_document(str(request.documents))
        clean_filename = Path(str(request.documents)).name.split('?')[0]
        answers = await answer_from_document_directly(content, clean_filename, request.questions)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        logging.info(f"Request completed in {processing_time:.2f} seconds.")
        
        if processing_time > 30:
            logging.warning(f"WARNING: Request took {processing_time:.2f} seconds, exceeding the 30-second target.")

        return QueryResponse(
            answers=answers,
            metadata={"document_name": clean_filename},
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