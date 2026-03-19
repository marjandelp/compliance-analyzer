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
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

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
    startTime = time.perf_counter()

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    sessionId = str(uuid.uuid4())
    filePath = os.path.join(UPLOAD_DIR, f"{sessionId}.pdf")

    logger.info(f"[{sessionId}] Analyze request started for file={file.filename}")



    try:
        stepStart = time.perf_counter()
        fileBytes = await file.read()

        if len(fileBytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if not checkIfPdf(fileBytes):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")

        with open(filePath, "wb") as buffer:
            buffer.write(fileBytes)

        if checkIfEncrypted(filePath):
            raise HTTPException(status_code=400, detail="Password protected PDFs are not supported.")

        stepStart = time.perf_counter()
        parsedText = parsePdf(filePath)
        logger.info(
            f"[{sessionId}] PDF parsed in {time.perf_counter() - stepStart:.2f}s | chars={len(parsedText)}"
        )

        # Empty parsed text 
        if not parsedText.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from this PDF.")

        stepStart = time.perf_counter()
        vectorStore = buildVectorStore(parsedText)
        logger.info(f"[{sessionId}] Vector store built in {time.perf_counter() - stepStart:.2f}s")


        sessionStore[sessionId] = {
            "vectorStore": vectorStore,
            "fullText": parsedText
        }

        stepStart = time.perf_counter()
        response = analyzeContract(vectorStore, parsedText)
        logger.info(f"[{sessionId}] Contract analysis finished in {time.perf_counter() - stepStart:.2f}s")

        response.sessionId = sessionId
        logger.info(f"[{sessionId}] Total /analyze time = {time.perf_counter() - startTime:.2f}s")


        return response

    except HTTPException:
        logger.exception(f"[{sessionId}] HTTP error during analyze")
        raise
    except Exception as e:
        logger.exception(f"[{sessionId}] Unexpected error during analyze: {e}")

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(filePath):
            os.remove(filePath)
            logger.info(f"[{sessionId}] Temp file removed")


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