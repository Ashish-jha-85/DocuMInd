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
import pandas as pd

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


def extract_text(file_path, file_type):
    """Extract text based on file type."""
    text = ""
    try:
        if file_type == "pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif file_type in ["docx", "doc"]:
            doc = docx.Document(file_path)
            # Only include non-empty paragraphs
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
        elif file_type == "txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif file_type == "csv":
            df = pd.read_csv(file_path, encoding="utf-8", errors="ignore")
            text = " ".join(df.astype(str).apply(lambda row: " ".join(row), axis=1))
        else:
            return ""
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return text.strip()


def extract_metadata(text):
    """Extract simple metadata."""
    lines = text.split("\n")
    title = lines[0].strip() if lines else None

    author_match = re.search(r"(Author|By):\s*(.+)", text, re.IGNORECASE)
    author = author_match.group(2).strip() if author_match else None

    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    date = date_match.group(0) if date_match else None

    doc = nlp(text[:2000])
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    return title, author, date, entities


def summarize_text(text, n=3):
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

    summary = " ".join(
        [s for s, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]]
    )
    return summary


def create_embedding(text):
    vec = embedder.encode(text)
    return pickle.dumps(vec)


@receiver(post_save, sender=Document)
def process_document(sender, instance, created, **kwargs):
    if created:
        file_path = instance.file.path
        # --- EDIT: Determine file type based on extension ---
        ext = os.path.splitext(file_path)[-1].lower()
        file_type = ext.replace(".", "")
        if file_type not in ["pdf", "docx", "doc", "txt", "csv"]:
            file_type = "other"

        # Save the detected type to the model
        instance.file_type = file_type
        instance.save(update_fields=["file_type"])

        # --- EDIT: Skip processing if type is "other" ---
        if file_type == "other":
            return

        # Extract text
        text = extract_text(file_path, file_type)
        if not text:
            return

        title, author, date, entities = extract_metadata(text)
        summary = summarize_text(text)

        # Classification
        classification = classifier(text, candidate_labels=CATEGORIES)
        predicted_category = classification["labels"][0]
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
            (title or "") + " " + (summary or "") if (title or summary) else text[:1000]
        )
        DocumentEmbedding.objects.update_or_create(
            document=instance, defaults={"vector": emb}
        )
