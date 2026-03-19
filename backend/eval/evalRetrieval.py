# eval/evalRetrieval.py
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("llama_parse").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import os
from openai import OpenAI
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings import buildVectorStore, retrieveChunks
from parser import parsePdf
from dotenv import load_dotenv


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COMPLIANCE_TOPICS = [
    {
        "topic": "Password Management",
        "question": "Does this text contain information about password policies, credential management, or authentication standards?"
    },
    {
        "topic": "IT Asset Management",
        "question": "Does this text contain information about asset inventory, configuration baselines, or infrastructure management?"
    },
    {
        "topic": "Security Training & Background Checks",
        "question": "Does this text contain information about security training, background screening, or personnel security?"
    },
    {
        "topic": "Data in Transit Encryption",
        "question": "Does this text contain information about encryption, TLS, data transmission security, or cipher suites?"
    },
    {
        "topic": "Network Authentication & Authorization Protocols",
        "question": "Does this text contain information about authentication protocols, MFA, RBAC, or access control?"
    }
]

def judgeRelevance(chunks: list[str], question: str) -> tuple[bool, str]:
    context = "\n\n---\n\n".join(chunks)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are evaluating whether retrieved document chunks are relevant to a compliance question. Respond with JSON only: {\"relevant\": true/false, \"reason\": \"brief explanation\"}"
            },
            {
                "role": "user",
                "content": f"""Question: {question}

Retrieved chunks:
{context}

Are these chunks relevant to the question?"""
            }
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )

    import json
    result = json.loads(response.choices[0].message.content)
    return result["relevant"], result["reason"]


def evalRetrieval(pdfPath: str, expectedRelevantCount: int = None):
    text = parsePdf(pdfPath)
    vectorStore = buildVectorStore(text, forceIndex=True)

    if vectorStore is None:
        print("Could not build vector store — document may be empty.")
        return

    print(f"Retrieval Evaluation: {os.path.basename(pdfPath)}")
    print("=" * 50)
    passed = 0

    for item in COMPLIANCE_TOPICS:
        chunks = retrieveChunks(vectorStore, query=item["topic"], k=6)

        if not chunks:
            print(f"{item['topic']}")
            print(f"  No relevant chunks retrieved \n")
            continue

        relevant, reason = judgeRelevance(chunks, item["question"])
        if relevant:
            passed += 1

        print(f"{item['topic']}")
        print(f"  Relevant: {'YES' if relevant else 'NO'}")
        print(f"  Reason: {reason}\n")

    print(f"Overall: {passed}/{len(COMPLIANCE_TOPICS)} topics retrieved relevant chunks")

    if expectedRelevantCount is not None:
        if passed == expectedRelevantCount:
            print(f"Expected {expectedRelevantCount} relevant topics — PASSED")
        else:
            print(f"Expected {expectedRelevantCount} relevant topics, got {passed} — FAILED")

    return passed


if __name__ == "__main__":
    evalRetrieval(
        "/Users/marjan/Desktop/manulife-project/contract-analyzer/test-pipeline-pdf/Sample Contract.pdf",
        expectedRelevantCount=5
    )

    evalRetrieval(
        "/Users/marjan/Desktop/manulife-project/contract-analyzer/test-pipeline-pdf/PCS Strategic Plan.pdf",
        expectedRelevantCount=0
    )
