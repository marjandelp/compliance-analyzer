import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from constants import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SHORT_DOC_THRESHOLD,
    EMBEDDING_MODEL
)

load_dotenv()

def buildVectorStore(text: str, forceIndex: bool = False) -> FAISS | None:
    # document is short enough to pass directly
    if not forceIndex and len(text) < SHORT_DOC_THRESHOLD:
        return None
    
    textSplitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )

    chunks = textSplitter.split_text(text)

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    vectorStore = FAISS.from_texts(
        chunks,
        embeddings,
        distance_strategy=DistanceStrategy.COSINE)

    return vectorStore


def retrieveChunks(vectorStore: FAISS, query: str, k: int = 6) -> list[str]:
    docs = vectorStore.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]

