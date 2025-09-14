from rest_framework.views import APIView
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import Document, DocumentEmbedding
from .signals import embedder  # use the same SentenceTransformer
from .models import Document, DocumentEmbedding, AccessLog
from django.db import models
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

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


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Superuser → see all. Normal user → only same-role or Unknown."""
        if self.request.user.is_superuser:
            return Document.objects.all().order_by("-created_at")

        return Document.objects.filter(
            models.Q(category=self.request.user.role) | models.Q(category="Unknown")
        ).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        """Return semantic search results if query is provided, else all docs"""
        query = request.query_params.get("query", "").strip()

        if query:  # Perform semantic search
            query_vec = embedder.encode(query).reshape(1, -1)
            results = []

            for emb in DocumentEmbedding.objects.select_related("document"):
                doc = emb.document
                # Superuser can see everything, normal users only their role
                if not request.user.is_superuser and doc.category != request.user.role:
                    continue

                doc_vec = pickle.loads(emb.vector).reshape(1, -1)
                score = cosine_similarity(query_vec, doc_vec)[0][0]
                results.append((score, doc))

            results.sort(key=lambda x: x[0], reverse=True)
            docs = [doc for _, doc in results[:5]]
        else:  # Default: all docs (filtered in get_queryset)
            docs = self.get_queryset()

        # ✅ Apply DRF pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10  # set page size
        result_page = paginator.paginate_queryset(docs, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        AccessLog.objects.create(user=request.user, document=instance, action="view")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        doc = serializer.save(
            uploader=self.request.user, category=self.request.user.role
        )
        AccessLog.objects.create(user=self.request.user, document=doc, action="upload")

    def perform_update(self, serializer):
        if not self.request.user.is_superuser and serializer.instance.category not in [
            self.request.user.role,
            "Unknown",
        ]:
            raise PermissionError("You are not allowed to update this document.")
        doc = serializer.save()
        AccessLog.objects.create(user=self.request.user, document=doc, action="update")

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser and instance.category not in [
            self.request.user.role,
            "Unknown",
        ]:
            raise PermissionError("You are not allowed to delete this document.")
        AccessLog.objects.create(
            user=self.request.user, document=instance, action="delete"
        )
        instance.delete()

    def pdf(self, request, pk=None):
        # Authenticate manually using token from query param
        token = request.query_params.get("token")
        if not token:
            raise AuthenticationFailed("Token required")

        user, _ = JWTAuthentication().get_user(
            validated_token=JWTAuthentication().get_validated_token(token)
        )
        request.user = user

        doc = self.get_object()
        file_path = doc.file.path
        if not os.path.exists(file_path):
            return Response({"error": "File not found"}, status=404)

        AccessLog.objects.create(user=user, document=doc, action="view")
        return FileResponse(open(file_path, "rb"), content_type="application/pdf")


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
        """Superuser → all logs. Normal → logs of same-role docs."""
        if self.request.user.is_superuser:
            return AccessLog.objects.select_related("document__uploader").order_by(
                "-timestamp"
            )

        user_role = self.request.user.role
        return (
            AccessLog.objects.select_related("document__uploader")
            .filter(document__uploader__role=user_role)
            .order_by("-timestamp")
        )


class DocumentStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # or allow any if public

    def get(self, request):
        total_docs = Document.objects.count()
        unknown_docs = Document.objects.filter(category="Unknown").count()
        hr_docs = Document.objects.filter(category="HR").count()
        invoice_docs = Document.objects.filter(category="Invoices").count()
        legal_docs = Document.objects.filter(category="Legal").count()
        contracts_docs = Document.objects.filter(category="Contracts").count()
        technical_reports_docs = Document.objects.filter(
            category="Technical Reports"
        ).count()

        return Response(
            {
                "total_documents": total_docs,
                "unknown_documents": unknown_docs,
                "hr_documents": hr_docs,
                "invoice_documents": invoice_docs,
                "legal_documents": legal_docs,
                "contracts_documents": contracts_docs,
                "technical_reports_documents": technical_reports_docs,
            }
        )
