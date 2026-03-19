
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import parsePdf
from embeddings import buildVectorStore
from analyzer import analyzeContract

def evalFaithfulness(pdfPath: str):
    text = parsePdf(pdfPath)
    vectorStore = buildVectorStore(text, forceIndex=True)
    response = analyzeContract(vectorStore, text)

    print("Faithfulness Evaluation\n" + "=" * 50)
    totalQuotes = 0
    faithfulQuotes = 0

    for result in response.results:
        print(f"{result.complianceQuestion}")
        for quote in result.relevantQuotes:
            totalQuotes += 1
            # check if quote appears in the original text
            if quote.strip().lower() in text.lower():
                faithfulQuotes += 1
                print(f"  Quote found in document")
            else:
                print(f" Quote NOT found — possible hallucination")
                print(f"  Quote: {quote[:100]}...")
        print()

    score = faithfulQuotes / totalQuotes if totalQuotes > 0 else 0
    print(f"Faithfulness Score: {faithfulQuotes}/{totalQuotes} quotes ({score:.0%})")
    print(f"Average quotes per question: {totalQuotes/len(response.results):.1f}")


if __name__ == "__main__":

    evalFaithfulness(
        "/Users/marjan/Desktop/manulife-project/contract-analyzer/test-pipeline-pdf/Sample Contract.pdf"
    )
