from fastapi import FastAPI, APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import tempfile
import aiofiles
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime
import asyncio
import hashlib
import json
import mimetypes
import shutil

# --- Correct Environment Variable Loading ---
# 1. Define the root directory of the script
ROOT_DIR = Path(__file__).parent
# 2. Use that ROOT_DIR variable to build the path to the .env file
dotenv_path = ROOT_DIR / '.env'
# 3. Load the environment variables from the .env file
load_dotenv(dotenv_path=dotenv_path, override=True)

# --- MongoDB Connection ---
# Now you can safely use the environment variables
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="Aura Intelligent Retrieval Engine",
    description="AI-powered document analysis and question answering system",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    documents: Optional[HttpUrl] = Field(None, description="URL to document (PDF/DOCX/TXT/Excel)")
    questions: List[str] = Field(..., min_items=1, max_items=50)
    
    @validator('questions')
    def validate_questions(cls, v):
        for question in v:
            if len(question.strip()) == 0:
                raise ValueError('Empty questions not allowed')
            if len(question) > 1000:
                raise ValueError('Question too long (max 1000 chars)')
        return [q.strip() for q in v]

class QueryResponse(BaseModel):
    answers: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float
    cache_hit: bool
    request_id: str

class DocumentSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    document_url: str
    document_name: str
    processed_chunks: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

class ChatHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question: str
    answer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Document Processing Functions ---
async def download_document(url: str) -> tuple[bytes, str]:
    """Download document from URL"""
    import httpx
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(str(url))
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download document: HTTP {response.status_code}")
        
        content_type = response.headers.get('content-type', '')
        return response.content, content_type

async def save_uploaded_file(upload_file: UploadFile) -> tuple[bytes, str, str]:
    """Save uploaded file and return content, content_type, filename"""
    try:
        # Read file content
        content = await upload_file.read()
        
        # Reset file pointer for later use
        await upload_file.seek(0)
        
        # Get content type and filename
        content_type = upload_file.content_type or 'application/octet-stream'
        filename = upload_file.filename or 'uploaded_document'
        
        return content, content_type, filename
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process uploaded file: {str(e)}")

async def process_document_with_gemini(content: bytes, filename: str, content_type: str) -> List[str]:
    """Process document using Gemini with file attachments"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Initialize Gemini chat
            chat = LlmChat(
                api_key=os.environ.get('GOOGLE_API_KEY'),
                session_id=str(uuid.uuid4()),
                system_message="You are an expert document analyzer. Extract and chunk meaningful content from documents for question answering."
            ).with_model("gemini", "gemini-2.0-flash")
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                if 'pdf' in content_type.lower() or filename.lower().endswith('.pdf'):
                    mime_type = 'application/pdf'
                elif 'word' in content_type.lower() or filename.lower().endswith(('.docx', '.doc')):
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif 'text' in content_type.lower() or filename.lower().endswith('.txt'):
                    mime_type = 'text/plain'
                elif 'excel' in content_type.lower() or filename.lower().endswith(('.xlsx', '.xls')):
                    mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                else:
                    mime_type = 'application/pdf'  # Default fallback
            
            # Create file attachment
            file_attachment = FileContentWithMimeType(
                file_path=temp_file_path,
                mime_type=mime_type
            )
            
            # Process document
            user_message = UserMessage(
                text="Please analyze this document and extract its content into meaningful chunks of 200-500 words each. Return only the extracted text chunks, separated by '---CHUNK---'. Do not include any analysis or commentary, just the raw content chunks.",
                file_contents=[file_attachment]
            )
            
            response = await chat.send_message(user_message)
            
            # Parse response into chunks
            if '---CHUNK---' in response:
                chunks = [chunk.strip() for chunk in response.split('---CHUNK---') if chunk.strip()]
            else:
                words = response.split()
                chunks = []
                current_chunk = []
                current_length = 0
                for word in words:
                    current_chunk.append(word)
                    current_length += len(word) + 1
                    if current_length > 400:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_length = 0
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
            
            return chunks[:20]  # Limit to 20 chunks max
            
        finally:
            try:
                os.unlink(temp_file_path)
            except OSError as e:
                logging.warning(f"Could not remove temp file {temp_file_path}: {e}")
                
    except Exception as e:
        logging.error(f"Document processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

async def answer_questions_with_context(questions: List[str], chunks: List[str], session_id: str) -> List[str]:
    """Answer questions using document context with Gemini"""
    try:
        context = "\n\n".join(chunks)
        tasks = [answer_single_question(question, context, session_id) for question in questions]
        answers = await asyncio.gather(*tasks)
        return answers
        
    except Exception as e:
        logging.error(f"Question answering error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")

async def answer_single_question(question: str, context: str, session_id: str) -> str:
    """Answer a single question with context"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=os.environ.get('GOOGLE_API_KEY'),
            session_id=session_id,
            system_message="You are an expert document analyst. Answer questions based strictly on the provided document context. Be precise, informative, and cite relevant parts of the document."
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""
        Based on the following document content, please answer the question accurately and comprehensively.
        
        DOCUMENT CONTENT:
        {context}
        
        QUESTION: {question}
        
        Please provide a detailed answer based only on the information in the document. If the document doesn't contain enough information to answer the question, please state that clearly.
        """
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
        
    except Exception as e:
        logging.error(f"Single question answering error: {e}", exc_info=True)
        return f"Error processing question: {str(e)}"

# --- API Routes ---
@api_router.get("/")
async def root():
    return {"message": "Aura Intelligent Retrieval Engine API", "version": "1.0.0"}

@api_router.post("/hackrx/run", response_model=QueryResponse)
async def process_document_query(request: QueryRequest):
    """Main endpoint for document analysis and question answering (URL-based)"""
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    logging.info(f"Processing URL-based request {request_id} for {len(request.questions)} questions")
    
    try:
        if not request.documents:
            raise HTTPException(status_code=400, detail="Document URL is required")
        
        session_id = str(uuid.uuid4())
        
        document_url = str(request.documents)
        document_name = Path(document_url).name or "document"
        
        content, content_type = await download_document(document_url)
        logging.info(f"Downloaded document: {len(content)} bytes, type: {content_type}")
        
        chunks = await process_document_with_gemini(content, document_name, content_type)
        logging.info(f"Processed document into {len(chunks)} chunks")
        
        session_data = DocumentSession(
            session_id=session_id,
            document_url=document_url,
            document_name=document_name,
            processed_chunks=chunks
        )
        await db.document_sessions.insert_one(session_data.dict(by_alias=True))
        
        answers = await answer_questions_with_context(request.questions, chunks, session_id)
        
        for question, answer in zip(request.questions, answers):
            chat_entry = ChatHistory(
                session_id=session_id,
                question=question,
                answer=answer
            )
            await db.chat_history.insert_one(chat_entry.dict(by_alias=True))
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return QueryResponse(
            answers=answers,
            metadata={
                "session_id": session_id,
                "document_name": document_name,
                "document_chunks": len(chunks),
                "model_used": "gemini-2.0-flash",
                "total_questions": len(request.questions),
                "source_type": "url"
            },
            processing_time=processing_time,
            cache_hit=False,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Request {request_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@api_router.post("/hackrx/upload", response_model=QueryResponse)
async def process_uploaded_document(file: UploadFile = File(...), questions: str = Form(...)):
    """Main endpoint for document analysis and question answering (file upload)"""
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    logging.info(f"Processing upload-based request {request_id}")
    
    try:
        try:
            questions_list = json.loads(questions)
            if not isinstance(questions_list, list) or len(questions_list) == 0:
                raise ValueError("Questions must be a non-empty list")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid questions format: {str(e)}")
        
        for q in questions_list:
            if not isinstance(q, str) or len(q.strip()) == 0:
                raise HTTPException(status_code=400, detail="Empty or invalid questions not allowed")
            if len(q) > 1000:
                raise HTTPException(status_code=400, detail="Question too long (max 1000 chars)")
        
        questions_list = [q.strip() for q in questions_list]
        session_id = str(uuid.uuid4())
        
        content, content_type, filename = await save_uploaded_file(file)
        logging.info(f"Uploaded file: {filename}, {len(content)} bytes, type: {content_type}")
        
        chunks = await process_document_with_gemini(content, filename, content_type)
        logging.info(f"Processed document into {len(chunks)} chunks")
        
        session_data = DocumentSession(
            session_id=session_id,
            document_url=f"uploaded://{filename}",
            document_name=filename,
            processed_chunks=chunks
        )
        await db.document_sessions.insert_one(session_data.dict(by_alias=True))
        
        answers = await answer_questions_with_context(questions_list, chunks, session_id)
        
        for question, answer in zip(questions_list, answers):
            chat_entry = ChatHistory(session_id=session_id, question=question, answer=answer)
            await db.chat_history.insert_one(chat_entry.dict(by_alias=True))
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return QueryResponse(
            answers=answers,
            metadata={
                "session_id": session_id,
                "document_name": filename,
                "document_chunks": len(chunks),
                "model_used": "gemini-2.0-flash",
                "total_questions": len(questions_list),
                "source_type": "upload"
            },
            processing_time=processing_time,
            cache_hit=False,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload request {request_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@api_router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session"""
    try:
        history_cursor = db.chat_history.find({"session_id": session_id})
        history = await history_cursor.to_list(100)
        
        serialized_history = []
        for entry in history:
            entry["id"] = str(entry.get("_id"))
            if isinstance(entry.get("timestamp"), datetime):
                entry["timestamp"] = entry["timestamp"].isoformat()
            serialized_history.append(entry)
        
        return {"session_id": session_id, "history": serialized_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db.list_collection_names()
        if not os.environ.get('GOOGLE_API_KEY'):
            raise Exception("Missing GOOGLE_API_KEY")
        
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "services": {"database": "connected", "gemini_api": "configured"}}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()})

# --- Main App Setup ---
# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()