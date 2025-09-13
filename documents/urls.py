from django.urls import path, include
from .views import SemanticSearchAPIView
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, DocumentEmbeddingViewSet, AccessLogViewSet

router = DefaultRouter()
router.register(r"documents", DocumentViewSet)
router.register(r"embeddings", DocumentEmbeddingViewSet)
router.register(r"accesslogs", AccessLogViewSet)

urlpatterns = [
    path("documents/search/", SemanticSearchAPIView.as_view(), name="semantic-search"),
    path("", include(router.urls)),
]
