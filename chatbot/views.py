# chatbot/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatSession
from transformers import pipeline
from .utils import create_chat_session
import google.generativeai as genai
from core import settings

# qa_pipeline = pipeline("question-answering")
# genai.configure(api_key="AIzaSyCUb59k-mrPSyUaat_TjZ_uHLRbEI3Q-vc")
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def answer_query(summary: str, query: str) -> str:
    """
    Ask Gemini to answer the question based on the summary.
    Provide short, precise, human-friendly answers suitable for questions like:
    - Who are you?
    - What is this platform?
    - What is in this data?
    """
    prompt = f"""
    You are DocuBot, an intelligent assistant for PDF summaries.
    Answer the user's question clearly, in one or two short sentences, without extra details.
    Use simple, human-friendly language generate short summary of each question.

    Document data:
    {summary}

    Question:
    {query}

    Answer:
    """

    try:
        response = model.generate_content(prompt)
        answer_text = response.text.strip()
        print("================== AI Response ==================")
        # print(answer_text)
        return answer_text
    except Exception as e:
        print("================== ERROR ==================")
        print("Error in answer_query:", str(e))
        return "Sorry, I couldn't generate an answer at this time."


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_question(request):
    session_id = request.data.get("session_id")
    question = request.data.get("question")

    if not session_id or not question:
        return Response({"error": "session_id and question are required."}, status=400)

    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return Response({"error": "Session not found or not yours."}, status=404)

    # Use document summary
    doc_summary = session.document.summary or ""
    if not doc_summary:
        return Response({"error": "Document summary is missing."}, status=400)

    # Get answer from Gemini
    answer = answer_query(doc_summary, question)
    # Update chat history
    session.history.append({"role": "user", "text": question})
    session.history.append({"role": "bot", "text": answer})
    session.save(update_fields=["history", "updated_at"])

    return Response(
        {
            "answer": answer,
            "session_id": session_id,
            "history": session.history,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_session(request):
    document_id = request.data.get("document_id")
    if not document_id:
        return Response({"error": "document_id is required"}, status=400)

    try:
        session_id = create_chat_session(request.user, document_id)
        session = ChatSession.objects.get(session_id=session_id)
        return Response(
            {
                "session_id": session_id,
                "history": session.history,  # will be []
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=400)
