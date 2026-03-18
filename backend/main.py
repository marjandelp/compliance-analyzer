import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from parser import parsePdf, checkIfEncrypted
from embeddings import buildVectorStore
from analyzer import analyzeContract
from chat import chat
from schemas import AnalysisResponse, ChatRequest, ChatResponse
import magic

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory session store: sessionId -> FAISS vector store
sessionStore: dict = {}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def checkIfPdf(fileBytes: bytes) -> bool:
    mimeType = magic.from_buffer(fileBytes, mime=True)
    return mimeType == "application/pdf"


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    sessionId = str(uuid.uuid4())
    filePath = os.path.join(UPLOAD_DIR, f"{sessionId}.pdf")

    try:
        fileBytes = await file.read()

        if len(fileBytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if not checkIfPdf(fileBytes):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")

        with open(filePath, "wb") as buffer:
            buffer.write(fileBytes)

        if checkIfEncrypted(filePath):
            raise HTTPException(status_code=400, detail="Password protected PDFs are not supported.")

        parsedText = parsePdf(filePath)

        # Empty parsed text 
        if not parsedText.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from this PDF.")


        vectorStore = buildVectorStore(parsedText)

        sessionStore[sessionId] = {
            "vectorStore": vectorStore,
            "fullText": parsedText
        }

        response = analyzeContract(vectorStore, parsedText)
        response.sessionId = sessionId

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(filePath):
            os.remove(filePath)


@app.post("/chat", response_model=ChatResponse)
async def chatEndpoint(request: ChatRequest):
    session = sessionStore.get(request.sessionId)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a contract first.")
    
    reply = chat(
        vectorStore=session["vectorStore"],
        userMessage=request.message,
        history=request.history,
        fullText=session["fullText"]
    )

    return ChatResponse(reply=reply)


@app.get("/health")
def health():
    return {"status": "ok"}