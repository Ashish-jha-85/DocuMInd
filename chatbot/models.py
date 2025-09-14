# chatbot/models.py
from django.db import models
from django.contrib.auth import get_user_model
from documents.models import Document
import pickle, json

User = get_user_model()


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    temp_embedding = models.BinaryField()  # Pickled embedding (optional now)
    history = models.JSONField(
        default=list
    )  # stores [{"role": "user", "text": "..."}, {"role": "bot", "text": "..."}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
