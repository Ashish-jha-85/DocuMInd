import os
import re
import pickle
import docx
import PyPDF2
import spacy
import numpy as np
from collections import Counter
from django.db.models.signals import post_save
from django.dispatch import receiver
from sentence_transformers import SentenceTransformer
from .models import Document, DocumentEmbedding
from transformers import pipeline


# Load NLP models only once
nlp = spacy.load("en_core_web_sm")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
CATEGORIES = [
    "Finance",
    "HR",
    "Legal",
    "Contracts",
    "Technical Reports",
    "Invoices",
    "Unknown",
]


def extract_text(file_path):
    """Extract text based on file type."""
    ext = os.path.splitext(file_path)[-1].lower()
    text = ""
    if ext == ".pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext in [".docx", ".doc"]:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    return text.strip()


def extract_metadata(text):
    """Extract simple metadata."""
    lines = text.split("\n")
    title = lines[0].strip() if lines else None

    # Author detection
    author_match = re.search(r"(Author|By):\s*(.+)", text, re.IGNORECASE)
    author = author_match.group(2).strip() if author_match else None

    # Date detection
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)  # YYYY-MM-DD
    date = date_match.group(0) if date_match else None

    # Entities
    doc = nlp(text[:2000])  # limit for speed
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    return title, author, date, entities


def summarize_text(text, n=3):
    """Extractive summary using word frequency scoring."""
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    if not sentences:
        return ""

    words = re.findall(r"\w+", text.lower())
    freq = Counter(words)
    scores = {}
    for sent in sentences:
        sent_words = re.findall(r"\w+", sent.lower())
        scores[sent] = sum(freq[w] for w in sent_words)

    # Top N sentences
    summary = " ".join(
        [s for s, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]]
    )
    return summary


def create_embedding(text):
    """Generate semantic embedding."""
    vec = embedder.encode(text)
    return pickle.dumps(vec)


@receiver(post_save, sender=Document)
def process_document(sender, instance, created, **kwargs):
    if created:  # only on first save
        file_path = instance.file.path
        text = extract_text(file_path)
        if not text:
            return

        title, author, date, entities = extract_metadata(text)
        summary = summarize_text(text)
        # --- 1. Classification ---
        classification = classifier(text, candidate_labels=CATEGORIES)
        predicted_category = classification["labels"][0]  # top predicted label
        instance.category = predicted_category
        # Update metadata
        instance.title = title or instance.title
        instance.author = author or instance.author
        instance.summary = summary
        if date:
            instance.date = date
        instance.entities = entities
        instance.save()

        # Save embedding
        emb = create_embedding(
            title + " " + summary if title or summary else text[:1000]
        )
        DocumentEmbedding.objects.update_or_create(
            document=instance, defaults={"vector": emb}
        )
