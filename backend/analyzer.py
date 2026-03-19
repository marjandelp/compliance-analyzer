import os
from dotenv import load_dotenv
from openai import OpenAI
from embeddings import retrieveChunks
from schemas import ComplianceResult, AnalysisResponse, ComplianceState
from langchain_community.vectorstores import FAISS
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
from constants import SYSTEM_PROMPT, COMPLIANCE_QUESTIONS, RETRIEVAL_K, ANALYSIS_MODEL
import logging
import time

logger = logging.getLogger(__name__)


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@retry(
    retry=retry_if_exception_type((openai.APITimeoutError, openai.RateLimitError)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3)
)
def analyzeQuestion(
    vectorStore: FAISS | None,
    topic: str,
    question: str,
    retrievalQueries: list[str],
    fullText: str = ""
) -> ComplianceResult:
    
    if vectorStore is None:
        context = fullText
    else:
        # multi-query retrieval: run each query and deduplicate
        seen = set()
        chunks = []
        for query in retrievalQueries:
            results = retrieveChunks(vectorStore, query=query, k=RETRIEVAL_K)
            for c in results:
                if c not in seen:
                    seen.add(c)
                    chunks.append(c)

        if not chunks:
            return ComplianceResult(
                complianceQuestion=topic,
                complianceState=ComplianceState.nonCompliant,
                confidence=0,
                relevantQuotes=[],
                rationale="No relevant information found in the contract for this compliance requirement."
            )

        context = "\n\n---\n\n".join(chunks)

    userPrompt = f"""Contract excerpts:
{context}

Compliance question:
{question}"""
    
    response = client.beta.chat.completions.parse(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": userPrompt}
        ],
        # temperature=0,
        response_format=ComplianceResult
    )

    return response.choices[0].message.parsed


def analyzeContract(vectorStore: FAISS | None, fullText: str = "") -> AnalysisResponse:
    startTime = time.perf_counter()
    logger.info("analyzeContract started")
    results = [None] * len(COMPLIANCE_QUESTIONS)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futureToIndex = {
            executor.submit(
                analyzeQuestion,
                vectorStore,
                item["topic"],
                item["question"],
                item["retrievalQueries"],
                fullText
            ): i
            for i, item in enumerate(COMPLIANCE_QUESTIONS)
        }

        for future in as_completed(futureToIndex): 
            index = futureToIndex[future]
            topic = COMPLIANCE_QUESTIONS[index]["topic"]
            index = futureToIndex[future]
            try:
                results[index] = future.result()
                logger.info(f"[{topic}] Completed")
            except Exception as e:
                logger.exception(f"[{topic}] Failed: {e}")
                print(f"ERROR for {COMPLIANCE_QUESTIONS[index]['topic']}: {str(e)}") 
  

                results[index] = ComplianceResult(
                    complianceQuestion=COMPLIANCE_QUESTIONS[index]["topic"],
                    complianceState=ComplianceState.nonCompliant,
                    confidence=0,
                    relevantQuotes=[],
                    rationale=f"Analysis failed for this requirement: {str(e)}"
                )
                
    logger.info(f"analyzeContract finished in {time.perf_counter() - startTime:.2f}s")
    return AnalysisResponse(results=results)
