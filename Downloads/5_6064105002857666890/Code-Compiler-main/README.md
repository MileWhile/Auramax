# Aura Intelligent Retrieval Engine

![Aura Logo](https://images.unsplash.com/photo-1628939824352-baa1cdddeb6b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzR8MHwxfHNlYXJjaHwzfHxpbnRlbGxpZ2VudCUyMHNlYXJjaCUyMHRlY2hub2xvZ3l8ZW58MHx8fGJsdWV8MTc1MzU1MjA3MHww&ixlib=rb-4.1.0&q=85)

## 🎯 Overview

Aura Intelligent Retrieval Engine is an enterprise-grade, AI-powered document analysis system that transforms any document into intelligent conversations. Upload or link to PDFs, Word documents, Excel files, or text documents and ask sophisticated questions powered by Google Gemini AI.

### Key Features
- 📄 **Multi-format Support**: PDF, DOCX, TXT, Excel (XLSX/XLS)
- 🔗 **Dual Input Methods**: Document URLs or file upload (drag-and-drop)
- 🤖 **AI-Powered Analysis**: Google Gemini 2.0 Flash for intelligent document processing
- 💬 **Multi-Question Processing**: Ask up to 10 questions simultaneously
- 🎨 **Beautiful Interface**: Professional dark theme with responsive design
- ⚡ **Fast Processing**: Optimized RAG pipeline with session management
- 📊 **Detailed Metrics**: Processing time, document chunks, and analysis metadata

## 🏗️ Architecture

### Technology Stack
- **Frontend**: React 18 + Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)
- **Database**: MongoDB (Local)
- **AI/LLM**: Google Gemini 2.0 Flash via emergentintegrations
- **File Processing**: Gemini native file processing with MIME type detection

### System Design
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React Client  │────▶│   FastAPI Server │────▶│   MongoDB       │
│                 │     │                  │     │                 │
│ • Document UI   │     │ • Document Proc. │     │ • Sessions      │
│ • File Upload   │     │ • RAG Pipeline   │     │ • Chat History  │
│ • Q&A Interface │     │ • Gemini API     │     │ • Metadata      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │   Google Gemini  │
                        │   2.0 Flash API  │
                        └──────────────────┘
```

## 📂 Project Structure

```
aura-intelligent-retrieval-engine/
├── backend/                    # FastAPI backend application
│   ├── server.py              # Main FastAPI application
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.css           # Custom styles
│   │   └── index.js          # React entry point
│   ├── public/               # Static assets
│   ├── package.json          # Node.js dependencies
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   └── .env                   # Frontend environment variables
├── README.md                  # This file
└── requirements-local.txt     # Local development dependencies
```

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**: [Download Python](https://python.org/downloads)
- **Node.js 18+**: [Download Node.js](https://nodejs.org)
- **MongoDB**: [Download MongoDB Community](https://www.mongodb.com/try/download/community)
- **Google API Key**: [Get from Google AI Studio](https://aistudio.google.com/app/apikey)

### 1. Clone/Extract Project
```bash
# If you have the zip file, extract it and navigate to the directory
cd aura-intelligent-retrieval-engine
```

### 2. Environment Setup

#### Backend Environment
Create `backend/.env` file:
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="aura_database"
GOOGLE_API_KEY="your_google_api_key_here"
```

#### Frontend Environment
Create `frontend/.env` file:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 3. Database Setup

#### Install and Start MongoDB
```bash
# On macOS with Homebrew
brew install mongodb-community
brew services start mongodb-community

# On Ubuntu/Debian
sudo apt-get install mongodb
sudo systemctl start mongod

# On Windows - Use MongoDB Compass or install via installer
```

#### Verify MongoDB is Running
```bash
# Connect to MongoDB
mongosh
# Should connect successfully to mongodb://127.0.0.1:27017
```

### 4. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install emergentintegrations (special package)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Start the backend server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Frontend Setup

```bash
# Open new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install
# OR
yarn install

# Start the development server
npm start
# OR
yarn start
```

### 6. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## 🔧 Configuration Details

### Backend Configuration (`backend/.env`)
```env
# Database Configuration
MONGO_URL="mongodb://localhost:27017"      # MongoDB connection string
DB_NAME="aura_database"                    # Database name

# AI Configuration
GOOGLE_API_KEY="your_api_key_here"         # Google Gemini API key

# Optional: Logging Level
LOG_LEVEL="INFO"                           # DEBUG, INFO, WARNING, ERROR
```

### Frontend Configuration (`frontend/.env`)
```env
# Backend API URL
REACT_APP_BACKEND_URL=http://localhost:8001

# Optional: Development settings
GENERATE_SOURCEMAP=false                   # Disable source maps in production
```

## 📋 API Endpoints

### Main Endpoints

#### 1. Process Document via URL
```http
POST /api/hackrx/run
Content-Type: application/json

{
  "documents": "https://example.com/document.pdf",
  "questions": [
    "What is the main topic of this document?",
    "What are the key findings?"
  ]
}
```

#### 2. Process Document via Upload
```http
POST /api/hackrx/upload
Content-Type: multipart/form-data

file: [uploaded file]
questions: ["What is this document about?", "Who is the author?"]
```

#### 3. Health Check
```http
GET /api/health
```

#### 4. Session History
```http
GET /api/sessions/{session_id}/history
```

### Response Format
```json
{
  "answers": [
    "This document discusses artificial intelligence...",
    "The key findings include improved accuracy..."
  ],
  "metadata": {
    "session_id": "uuid-string",
    "document_name": "example.pdf",
    "document_chunks": 5,
    "model_used": "gemini-2.0-flash",
    "total_questions": 2,
    "source_type": "url"
  },
  "processing_time": 3.45,
  "cache_hit": false,
  "request_id": "uuid-string"
}
```

## 🧪 Testing

### Health Check
```bash
# Test backend health
curl http://localhost:8001/api/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "services": {
    "database": "connected",
    "gemini_api": "configured"
  }
}
```

### Document Processing Test
```bash
# Test with sample PDF
curl -X POST "http://localhost:8001/api/hackrx/run" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "questions": ["What is this document about?"]
  }'
```

## 🔍 File Details

### Backend Files

#### `backend/server.py` (1,200+ lines)
Main FastAPI application containing:
- **Document Processing**: URL download and file upload handling
- **Gemini Integration**: AI-powered document analysis using emergentintegrations
- **RAG Pipeline**: Intelligent question answering with context
- **Session Management**: MongoDB storage for chat history
- **API Endpoints**: RESTful API with comprehensive error handling
- **Health Monitoring**: System status and diagnostics

Key Functions:
- `download_document()`: Downloads documents from URLs
- `save_uploaded_file()`: Handles file uploads with validation
- `process_document_with_gemini()`: AI document processing
- `answer_questions_with_context()`: RAG-based question answering

#### `backend/requirements.txt`
Python dependencies including:
- `fastapi==0.111.0`: Modern web framework
- `emergentintegrations`: Custom LLM integration library
- `motor==3.3.2`: Async MongoDB driver
- `httpx==0.27.0`: HTTP client for document downloads
- `aiofiles==24.1.0`: Async file operations

### Frontend Files

#### `frontend/src/App.js` (600+ lines)
Main React component featuring:
- **Dual Input Modes**: URL input and file upload with drag-and-drop
- **Question Management**: Dynamic question addition/removal (up to 10)
- **File Validation**: Type and size validation for uploads
- **Results Display**: Beautiful Q&A interface with metadata
- **Error Handling**: User-friendly error messages
- **Responsive Design**: Mobile-first responsive layout

Key Features:
- File drag-and-drop with visual feedback
- Form validation and submission
- Loading states and progress indicators
- Results visualization with statistics

#### `frontend/src/App.css` (200+ lines)
Custom CSS with:
- **Tailwind Integration**: Base Tailwind CSS imports
- **Custom Animations**: Gradient effects, loading animations
- **Responsive Utilities**: Mobile-optimized styles
- **Component Styling**: Custom scrollbars, focus states
- **Theme Variables**: Dark theme color scheme

## 🛠️ Troubleshooting

### Common Issues

#### 1. MongoDB Connection Failed
```
Error: MongoServerError: connection refused
```
**Solution**:
```bash
# Check if MongoDB is running
brew services list | grep mongodb
# OR
sudo systemctl status mongod

# Start MongoDB if not running
brew services start mongodb-community
# OR
sudo systemctl start mongod
```

#### 2. Google API Key Invalid
```
Error: Missing GOOGLE_API_KEY
```
**Solution**:
1. Get API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Update `backend/.env` file with your key
3. Restart the backend server

#### 3. emergentintegrations Installation Failed
```
Error: Could not find a version that satisfies emergentintegrations
```
**Solution**:
```bash
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

#### 4. Port Already in Use
```
Error: Address already in use
```
**Solution**:
```bash
# Kill process using port 8001 (backend)
lsof -ti:8001 | xargs kill -9

# Kill process using port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

#### 5. File Upload Not Working
- Check file size (max 10MB)
- Verify file type (PDF, DOCX, TXT, Excel)
- Ensure backend is running on correct port
- Check browser console for JavaScript errors

### Performance Optimization

#### For Large Documents
- Documents are automatically chunked for processing
- Maximum 20 chunks per document to prevent memory issues
- Processing time scales with document size and question count

#### For Multiple Questions
- Questions are processed in parallel for faster results
- Recommended: 3-5 questions for optimal performance
- Maximum: 10 questions per request

## 🔒 Security Considerations

### Local Development
- API keys are stored in environment files (not committed to version control)
- CORS is configured for local development
- File uploads are validated for type and size

### Production Deployment
For production use, consider:
- Enable HTTPS/SSL certificates
- Configure proper CORS origins
- Implement rate limiting
- Add authentication/authorization
- Use environment variable management
- Set up monitoring and logging

## 📈 Monitoring and Logging

### Health Monitoring
- Health check endpoint: `/api/health`
- MongoDB connection status
- Google API configuration status

### Logging
- Backend logs all requests and processing times
- Error logging for debugging
- Session tracking for usage analytics

### Metrics Available
- Processing time per request
- Document chunk count
- Question processing success rate
- Session creation and history

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

### Code Style
- Backend: Follow PEP 8 Python standards
- Frontend: ESLint and Prettier configuration
- Comments: Document complex logic
- Testing: Add tests for new features

## 📄 License

This project is private and proprietary. All rights reserved.

## 🔗 Links and Resources

- [Google AI Studio](https://aistudio.google.com) - Get your API key
- [MongoDB Documentation](https://docs.mongodb.com) - Database setup
- [FastAPI Documentation](https://fastapi.tiangolo.com) - Backend framework
- [React Documentation](https://reactjs.org/docs) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/docs) - Styling framework

## 📞 Support

For technical support or questions:
1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Check logs for detailed error messages
4. Verify all prerequisites are installed correctly

---

**Built with ❤️ using Google Gemini 2.0 Flash and modern web technologies**
