from django.urls import path
from . import views

urlpatterns = [
    path("ask-question/", views.ask_question, name="ask-question"),
    path("create-session/", views.create_session, name="create-session"),
]
