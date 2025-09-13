from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Document, DocumentEmbedding
from .signals import embedder  # use the same SentenceTransformer
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .serializers import DocumentSerializer


class SemanticSearchAPIView(APIView):
    # permission_classes = [IsAuthenticated]

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
            # if doc.category != request.user.role:
            #     continue

            doc_vec = pickle.loads(emb.vector).reshape(1, -1)
            score = cosine_similarity(query_vec, doc_vec)[0][0]
            results.append((score, doc))

        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)

        # Serialize top 5
        serializer = DocumentSerializer([doc for _, doc in results[:5]], many=True)
        return Response(serializer.data)
