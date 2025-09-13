from django.urls import path
from .views import SemanticSearchAPIView

urlpatterns = [
    path("search/", SemanticSearchAPIView.as_view(), name="semantic-search"),
]
