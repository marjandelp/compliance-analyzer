import json
from parser import parsePdf
from embeddings import buildVectorStore
from analyzer import analyzeContract

PDF_PATH = "/Users/marjan/Desktop/manulife-project/contract-analyzer/test-pipeline-pdf/Sample Contract.pdf"

def main():
    print("Step 1: Parsing PDF...")
    text = parsePdf(PDF_PATH)
    print(f"Parsed {len(text)} characters")
    print(f"Preview:\n{text}\n")

    print("Step 2: Building vector store...")
    vectorStore = buildVectorStore(text)
    print("Vector store built successfully\n")

    print("Step 3: Running compliance analysis...")
    response = analyzeContract(vectorStore)

    print("Results:\n")
    for result in response.results:
        print(f"Question: {result.complianceQuestion}")
        print(f"State:    {result.complianceState}")
        print(f"Confidence: {result.confidence}%")
        print(f"Rationale: {result.rationale}")
        print(f"Quotes: {result.relevantQuotes}")
        print("-" * 60)

if __name__ == "__main__":
    main()