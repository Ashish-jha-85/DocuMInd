import requests
import os
import tempfile
import PyPDF2
import docx
from transformers import pipeline

# Predefined categories
CATEGORIES = ["Finance", "HR", "Legal", "Contracts", "Technical Reports", "Invoices"]

# Hugging Face pipeline (zero-shot classification)
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def download_file(url):
    """Download file from URL and save to temp file."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download {url}")
    ext = url.split(".")[-1].lower()
    fd, path = tempfile.mkstemp(suffix="." + ext)
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(response.content)
    return path, ext


def extract_text(file_path, ext):
    """Extract text from PDF, DOCX, or TXT."""
    text = ""
    if ext == "pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext in ["docx", "doc"]:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    elif ext == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        raise Exception("Unsupported file type: " + ext)
    return text.strip()


def classify_document(text):
    """Classify text into predefined categories."""
    result = classifier(text, candidate_labels=CATEGORIES)
    return result["labels"][0], result["scores"][0]


def classify_from_url(url):
    path, ext = download_file(url)
    try:
        text = extract_text(path, ext)
        if not text:
            raise Exception("No text extracted from document.")
        label, score = classify_document(text[:1000])  # use first 1000 chars for speed
        return {"url": url, "category": label, "confidence": round(score, 4)}
    finally:
        os.remove(path)


if _name_ == "_main_":
    # Example usage
    urls = [
        "https://arxiv.org/pdf/1706.03762.pdf",  # Example: Technical Report (Transformer paper)
        # Add more document URLs here...
    ]
    for url in urls:
        try:
            result = classify_from_url(url)
            print(result)
        except Exception as e:
            print(f"Error processing {url}: {e}")
