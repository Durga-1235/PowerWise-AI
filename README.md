# ⚡ PowerWise AI

### AI-Powered Voice Chatbot Based on The 48 Laws of Power

PowerWise AI is an interactive AI-powered chatbot that helps users understand the 48 Laws of Power through natural conversations. Users can type their questions or speak using the microphone, and the chatbot generates clear answers with automatic voice output.

## Features

- **AI-Powered Conversations:** Ask questions about the 48 Laws of Power.
- **Voice Input:** Speak questions using the microphone.
- **Text-to-Speech:** Automatically converts AI responses into voice.
- **Stop Voice:** Stop audio playback instantly.
- **Law-Based Knowledge:** Provides explanations and practical examples.
- **Interactive Interface:** Clean and user-friendly chat interface.
- **New Conversation:** Start a fresh conversation whenever needed.

## Technology Stack

**Frontend**
- React.js
- Vite
- CSS

**Backend**
- Python
- FastAPI

**AI and Voice**
- Groq API
- Whisper for speech recognition
- Edge TTS for voice generation

## Project Structure

```text
PowerWise-AI/
├── backend/
│   ├── knowledge/
│   ├── main.py
│   └── test_groq.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   └── package.json
└── .gitignore
```

## How It Works

1. The user enters a question through text or voice.
2. Voice input is converted into text using speech recognition.
3. The backend processes the question using the AI model.
4. The chatbot generates a relevant response.
5. Text-to-speech converts the response into audio.
6. The user can listen to or stop the generated voice.

## Installation and Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Configure the Groq API key in the backend `.env` file before running the application.

## Future Enhancements

- Multilingual voice conversations.
- Improved law-based recommendations.
- Conversation history.
- Enhanced response personalization.

## Author

**Durga T**

B.Tech – Artificial Intelligence and Data Science
