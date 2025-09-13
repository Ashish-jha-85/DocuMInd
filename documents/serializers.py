from rest_framework import serializers
from .models import Document, DocumentEmbedding, AccessLog


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "category", "author", "date", "summary", "file"]


class DocumentEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentEmbedding
        fields = "__all__"


class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = "__all__"
