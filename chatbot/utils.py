# chatbot/utils.py
import pickle
import uuid
from documents.models import Document
from documents.signals import embedder


def create_chat_session(user, document_id):
    doc = Document.objects.get(id=document_id)

    # Use summary instead of full text
    text = doc.summary or ""
    if not text:
        raise ValueError("Document summary is missing.")

    # Optional: still create embedding on summary if you need semantic search
    temp_emb = embedder.encode(text)
    temp_emb_pickle = pickle.dumps(temp_emb)

    from .models import ChatSession

    session = ChatSession.objects.create(
        user=user,
        document=doc,
        session_id=str(uuid.uuid4()),
        temp_embedding=temp_emb_pickle,
        history=[],
    )
    return session.session_id
