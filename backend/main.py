from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
from pydantic import BaseModel
import re
import os
from dotenv import load_dotenv
from groq import Groq
import edge_tts
from fastapi.responses import FileResponse

load_dotenv(Path(__file__).resolve().parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI(
    title="PowerWise AI",
    description="Voice AI Assistant based on The 48 Laws of Power",
    version="1.0.0"
)

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Load 48 Laws Knowledge Base
# -----------------------------

BASE_DIR = Path(__file__).resolve().parent
LAWS_FILE = BASE_DIR / "knowledge" / "laws.json"

with open(LAWS_FILE, "r", encoding="utf-8") as file:
    laws = json.load(file)


# -----------------------------
# Home
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "PowerWise AI is running!",
        "project": "48 Laws of Power Voice Chatbot",
        "total_laws": len(laws)
    }


# -----------------------------
# Health Check
# -----------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "knowledge_base": "loaded",
        "total_laws": len(laws)
    }


# -----------------------------
# Get All Laws
# -----------------------------

@app.get("/laws")
def get_all_laws():
    return {
        "total": len(laws),
        "laws": laws
    }


# -----------------------------
# Get One Law
# -----------------------------

@app.get("/laws/{law_number}")
def get_law(law_number: int):

    for law in laws:
        if law["law_number"] == law_number:
            return law

    return {
        "error": "Law not found"
    }


# -----------------------------
# Search Laws
# -----------------------------

@app.get("/search")
def search_laws(query: str):

    query = query.lower()

    results = []

    for law in laws:

        searchable_text = (
            law["title"] + " " +
            law["summary"] + " " +
            " ".join(law["keywords"])
        ).lower()

        if query in searchable_text:
            results.append(law)

    return {
        "query": query,
        "results_found": len(results),
        "results": results
    }
   


class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def chat(request: ChatRequest):

    question = request.question.strip()

    if not question:
        return {
            "answer": "Please ask a question.",
            "law": None
        }

    # Find relevant laws
    question_lower = question.lower()
    relevant_laws = []

    for law in laws:
        searchable_text = (
            law["title"] + " " +
            law["summary"] + " " +
            " ".join(law["keywords"])
        ).lower()

        if any(word in searchable_text for word in question_lower.split()):
            relevant_laws.append(law)

    if not relevant_laws:
        relevant_laws = laws[:5]

    context = "\n\n".join(
        f"Law {law['law_number']} - {law['title']}\n"
        f"{law['summary']}"
        for law in relevant_laws[:5]
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": """
You are PowerWise AI, a professional voice-based
strategic thinking assistant based on The 48 Laws of Power.

RESPONSE RULES:

1. Understand the user's question before answering.
2. Respond in the same language as the user's question.
3. Give a direct and useful introduction.
4. Explain only the most relevant laws.
5. Present each law separately, one below another.
6. Use this exact structure:

Law 1 - Law Title

Explanation in simple and clear language.

Practical Example:
Give a realistic example.

Law 2 - Law Title

Explanation in simple and clear language.

Practical Example:
Give a realistic example.

7. Use proper paragraph spacing.
8. Finish with a short practical conclusion.
9. Keep the answer professional, clear and conversational.
10. Explain concepts in a way that is easy to understand
    when spoken aloud.

STRICT FORMATTING RULES:

- Never use Markdown symbols such as **, ###, or ``` .
- Never use HTML tags such as <br>.
- Never use tables or pipe separators.
- Never combine multiple laws into one paragraph.
- Never invent law numbers or unsupported facts.
- Do not read out formatting instructions.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Available knowledge:\n{context}\n\n"
                    f"User question: {question}"
                )
            }
        ],
        temperature=0.3,
        max_completion_tokens=700
    )

    answer = response.choices[0].message.content.strip()

    return {
        "answer": answer,
        "law": relevant_laws[0] if relevant_laws else None
    }

@app.post("/voice-to-text")
async def voice_to_text(audio: UploadFile = File(...)):

    audio_data = await audio.read()

    transcription = client.audio.transcriptions.create(
        file=(audio.filename or "audio.webm", audio_data),
        model="whisper-large-v3",
        response_format="text"
    )

    return {
        "transcribed_text": transcription
    }

@app.post("/text-to-speech")
async def text_to_speech(request: ChatRequest):

    text = request.question.strip()

    if not text:
        return {"error": "Text is required"}

    audio_path = Path(__file__).resolve().parent / "response.mp3"

    # Detect Tamil or English
    voice = (
        "ta-IN-PallaviNeural"
        if any("\u0B80" <= char <= "\u0BFF" for char in text)
        else "en-US-AriaNeural"
    )

    communicate = edge_tts.Communicate(
        text,
        voice=voice
    )

    await communicate.save(str(audio_path))

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename="response.mp3"
    )

@app.get("/audio")
def get_audio():
    audio_path = Path(__file__).resolve().parent / "response.mp3"

    if not audio_path.exists():
        return {"error": "Audio file not found"}

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename="response.mp3"
    )

