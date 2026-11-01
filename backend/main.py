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

    question_lower = question.lower()

    # Ignore common words while searching for matching laws
    stop_words = {
        "what", "is", "the", "a", "an", "of", "in", "on",
        "to", "for", "and", "or", "explain", "tell", "me",
        "about", "how", "can", "i", "please", "give",
        "with", "this", "that", "does", "do", "who"
    }

    question_words = {
        word for word in re.findall(r"[a-zA-Z0-9]+", question_lower)
        if len(word) > 2 and word not in stop_words
    }

    relevant_laws = []

    # Check whether the user asked about a specific law number
    law_match = re.search(
        r"\blaw\s*(?:number\s*)?(\d{1,2})\b",
        question_lower
    )

    if law_match:
        requested_number = int(law_match.group(1))

        relevant_laws = [
            law for law in laws
            if law.get("law_number") == requested_number
        ]

    else:
        # Search for laws using titles, summaries and keywords
        scored_laws = []

        for law in laws:

            searchable_text = " ".join([
                str(law.get("title", "")),
                str(law.get("summary", "")),
                " ".join(law.get("keywords", []))
            ]).lower()

            law_words = set(
                re.findall(r"[a-zA-Z0-9]+", searchable_text)
            )

            score = len(question_words.intersection(law_words))

            if score > 0:
                scored_laws.append((score, law))

        # Select only the most relevant laws
        scored_laws.sort(key=lambda item: item[0], reverse=True)

        if scored_laws:
            highest_score = scored_laws[0][0]

            relevant_laws = [
                law for score, law in scored_laws
                if score == highest_score
            ][:3]

    # Prepare knowledge context only when relevant laws are found
    if relevant_laws:
        context = "\n\n".join(
            f"Law {law['law_number']} - {law['title']}\n"
            f"{law['summary']}"
            for law in relevant_laws
        )
    else:
        context = "No directly matching law was found in the knowledge base."

    system_prompt = """
You are PowerWise AI, a helpful and professional AI assistant.

You can answer BOTH:
1. Questions about The 48 Laws of Power.
2. General questions about technology, programming, AI,
   education, careers, science, and everyday topics.

IMPORTANT RULES:

1. First understand what the user is asking.
2. Answer the actual question directly.
3. Respond in the same language as the user.
4. If the question is about The 48 Laws of Power,
   use the supplied law knowledge when relevant.
5. If the question is a general question,
   answer it normally using your general knowledge.
6. NEVER force a general question into a 48 Laws of Power answer.
7. NEVER mention a law if it is not relevant to the question.
8. If the supplied knowledge does not contain the answer
   to a specific law question, say so honestly.
9. Give simple explanations and practical examples when useful.
10. Do not invent facts or law numbers.
11. Keep answers clear, professional and conversational.
12. Do not use Markdown symbols, HTML tags or tables.
13. Make the answer easy to understand when spoken aloud.
"""

    user_prompt = f"""
Question from user:
{question}

Relevant knowledge from The 48 Laws of Power:
{context}

Answer the user's actual question.
If it is a general question, answer it as a general AI assistant.
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
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

    except Exception as e:
        return {
            "answer": "Sorry, I am unable to process your question right now. Please try again.",
            "law": None,
            "error": str(e)
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

