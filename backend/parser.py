
import os
from dotenv import load_dotenv
from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader
import fitz 


load_dotenv()

def checkIfEncrypted(filePath: str) -> bool:
    with fitz.open(filePath) as doc:
        return doc.is_encrypted

def parsePdf(filePath: str) -> str:
    if not os.path.exists(filePath):
        raise FileNotFoundError(f"PDF not found at path: {filePath}")

    # Try LlamaParse first
    try:
        parser = LlamaParse(
            api_key=os.getenv("LLAMA_API_KEY"),
            result_type="markdown",
            verbose=False,
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name="openai-gpt4o"
        )

        fileExtractor = {".pdf": parser}

        documents = SimpleDirectoryReader(
            input_files=[filePath],
            file_extractor=fileExtractor
        ).load_data()

        fullText = "\n\n".join([doc.text for doc in documents])

        if fullText.strip():
            return fullText

    except Exception as e:
        print(f"LlamaParse failed, falling back to PyMuPDF: {str(e)}")

    # Fallback to PyMuPDF
    try:
        doc = fitz.open(filePath)
        fullText = "\n\n".join([page.get_text() for page in doc])
        doc.close()

        if not fullText.strip():
            raise ValueError("Could not extract any text from the PDF.")

        return fullText

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")