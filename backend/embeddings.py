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


# ey decisions you can explain in the interview:

# chunk_size=512 — small enough to be precise for retrieval, large enough to capture a full clause
# chunk_overlap=64 — prevents a compliance clause from being split across two chunks and missed
# k=6 — retrieves 6 chunks per question; enough context without blowing up the prompt
# text-embedding-3-small — cheap, fast, good enough for legal text; large is better but overkill here


# On k=6:
# It's a RAG hyperparameter — how many chunks to retrieve per question. Here's the reasoning:

# Each chunk is ~512 tokens
# k=6 means ~3000 tokens of context fed to GPT-4o per question
# GPT-4o's context window is 128k tokens so we have plenty of room
# We chose 6 because:

# Too few (k=2-3) — might miss a relevant clause split across chunks
# Too many (k=10+) — adds noise, irrelevant chunks confuse the model, costs more
# 6 is a sweet spot for a single-topic compliance question



# In the interview you can say: "k=6 was chosen empirically — enough to capture a full clause with surrounding context, without adding noise. In production I'd tune this by evaluating retrieval precision on a labeled set of contracts."