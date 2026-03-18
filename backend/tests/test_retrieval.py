import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings import buildVectorStore, retrieveChunks

SAMPLE_TEXT = """
This agreement requires all passwords to be at least 12 characters long.
Vendors must implement multi-factor authentication for all administrative access.
Data in transit must be encrypted using TLS 1.2 or higher.
All assets must be inventoried quarterly including cloud accounts and databases.
Security awareness training is required on hire and annually thereafter.
Background checks are required for all personnel with access to company data.
Network access must use SAML SSO and OAuth 2.0 for API authentication.
Break-glass credentials must be rotated every 90 days.
""" * 10  # repeat to ensure enough text for chunking

def test_buildVectorStoreReturnsNoneForShortText():
    shortText = "This is a very short document."
    result = buildVectorStore(shortText)
    assert result is None

def test_buildVectorStoreReturnsFAISSForLongText():
    result = buildVectorStore(SAMPLE_TEXT, forceIndex=True)
    assert result is not None

def test_retrieveChunksReturnsResults():
    vectorStore = buildVectorStore(SAMPLE_TEXT, forceIndex=True)
    chunks = retrieveChunks(vectorStore, query="password management", k=3)
    assert len(chunks) > 0

def test_retrieveChunksAreNonEmpty():
    vectorStore = buildVectorStore(SAMPLE_TEXT, forceIndex=True)
    chunks = retrieveChunks(vectorStore, query="encryption TLS", k=3)
    for chunk in chunks:
        assert chunk.strip() != ""

def test_retrieveChunksRespectKLimit():
    vectorStore = buildVectorStore(SAMPLE_TEXT, forceIndex=True)
    chunks = retrieveChunks(vectorStore, query="authentication", k=3)
    assert len(chunks) <= 3