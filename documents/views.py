from rest_framework.views import APIView
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import Document, DocumentEmbedding
from .signals import embedder  # use the same SentenceTransformer
from .models import Document, DocumentEmbedding, AccessLog


import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .serializers import (
    DocumentSerializer,
    DocumentEmbeddingSerializer,
    AccessLogSerializer,
)


class SemanticSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "")
        if not query:
            return Response({"error": "Query is required"}, status=400)

        # Generate query embedding
        query_vec = embedder.encode(query).reshape(1, -1)

        results = []
        for emb in DocumentEmbedding.objects.select_related("document"):
            doc = emb.document
            # Optional: Role-based filter
            if doc.category != request.user.role:
                print(doc.category, request.user.role)
                continue

            doc_vec = pickle.loads(emb.vector).reshape(1, -1)
            score = cosine_similarity(query_vec, doc_vec)[0][0]
            results.append((score, doc))

        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)

        # Serialize top 5
        serializer = DocumentSerializer([doc for _, doc in results[:5]], many=True)
        return Response(serializer.data)


from .models import Document, AccessLog
from .serializers import DocumentSerializer
from rest_framework import viewsets, permissions


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()  # needed for DRF router
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(category=self.request.user.role).order_by(
            "-created_at"
        )

    def retrieve(self, request, *args, **kwargs):
        """Called when fetching a single document (GET /documents/{id}/)"""
        instance = self.get_object()
        AccessLog.objects.create(user=request.user, document=instance, action="view")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Save document and capture instance
        doc = serializer.save(
            uploader=self.request.user, category=self.request.user.role
        )
        # ✅ Log upload
        AccessLog.objects.create(user=self.request.user, document=doc, action="upload")

    def perform_update(self, serializer):
        if serializer.instance.category != self.request.user.role:
            raise PermissionError("You are not allowed to update this document.")
        doc = serializer.save()
        # ✅ Log update
        AccessLog.objects.create(user=self.request.user, document=doc, action="update")

    def perform_destroy(self, instance):
        if instance.category != self.request.user.role:
            raise PermissionError("You are not allowed to delete this document.")
        # ✅ Log delete
        AccessLog.objects.create(
            user=self.request.user, document=instance, action="delete"
        )
        instance.delete()


class DocumentEmbeddingViewSet(viewsets.ModelViewSet):
    queryset = DocumentEmbedding.objects.all()
    serializer_class = DocumentEmbeddingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only return embeddings for documents uploaded by users of the same role as current user.
        """
        user_role = self.request.user.role
        return DocumentEmbedding.objects.select_related("document__uploader").filter(
            document__uploader__role=user_role
        )


class AccessLogViewSet(viewsets.ModelViewSet):
    queryset = AccessLog.objects.all().order_by("-timestamp")
    serializer_class = AccessLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only return logs for documents uploaded by users of the same role as current user.
        """
        user_role = self.request.user.role
        return (
            AccessLog.objects.select_related("document__uploader")
            .filter(document__uploader__role=user_role)
            .order_by("-timestamp")
        )
