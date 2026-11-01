
import { useEffect, useState, useRef } from "react";
import "./App.css";

const API = "https://powerwise-ai-oldt.onrender.com";

// Clean unwanted formatting before displaying and speaking
const cleanResponse = (text = "") => {
  return String(text)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/?[^>]+>/g, "")
    .replace(/\r\n/g, "\n")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/^\s*[-*_]{3,}\s*$/gm, "")
    .replace(/```/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
};

function App() {
  const messagesEndRef = useRef(null);
  const [laws, setLaws] = useState([]);
  const [question, setQuestion] = useState("");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Welcome to PowerWise AI. Ask me anything about the 48 Laws of Power."
    }
  ]);

  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const audioRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioUrlRef = useRef(null);

// Load all 48 laws
useEffect(() => {
  fetch(`${API}/laws`)
    .then((res) => {
      if (!res.ok) throw new Error("Unable to load laws");
      return res.json();
    })
    .then((data) => setLaws(data.laws || []))
    .catch((err) => console.error("Laws loading error:", err));
    }, []);

  


  // Auto-scroll when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages]);

  // Stop current voice immediately
  const stopVoice = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }

    setIsSpeaking(false);
  };


  // Start microphone recording
  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone is not supported by this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true
      });

      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks = [];

      recorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsRecording(false);

        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        try {
          const audioBlob = new Blob(audioChunks, {
            type: mediaRecorder.mimeType || "audio/webm"
          });

          if (!audioBlob.size) {
            throw new Error("No audio was recorded.");
          }

          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.webm");

          const response = await fetch(`${API}/voice-to-text`, {
            method: "POST",
            body: formData
          });

          if (!response.ok) {
            throw new Error("Voice transcription failed.");
          }
const data = await response.json();
const transcribedText = (data.transcribed_text || "").trim();

if (transcribedText) {
  setQuestion(transcribedText);
  await sendMessage(transcribedText);
}
        } catch (error) {
          console.error("Transcription error:", error);
          alert("Unable to transcribe your voice. Please try again.");
        }
      };

      mediaRecorder.start();
      setIsRecording(true);

    } catch (error) {
      console.error("Microphone error:", error);
      alert(error.message || "Please allow microphone permission.");
    }
  };

  // Stop microphone recording
  const stopRecording = () => {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  };

  // Play generated AI voice
  const playVoice = async (text) => {
    try {
      stopVoice();

      const response = await fetch(`${API}/text-to-speech`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: text
        })
      });

      if (!response.ok) {
        throw new Error("Voice generation failed.");
      }

      const audioBlob = await response.blob();
      const audioURL = URL.createObjectURL(audioBlob);

      audioUrlRef.current = audioURL;

      const audio = new Audio(audioURL);
      audioRef.current = audio;

      audio.onended = () => {
        if (audioRef.current === audio) {
          audioRef.current = null;
          setIsSpeaking(false);

          if (audioUrlRef.current) {
            URL.revokeObjectURL(audioUrlRef.current);
            audioUrlRef.current = null;
          }
        }
      };

      audio.onerror = () => {
        if (audioRef.current === audio) {
          audioRef.current = null;
          setIsSpeaking(false);
        }
      };

      setIsSpeaking(true);

      await audio.play();

    } catch (error) {
      console.error("Voice playback error:", error);
      setIsSpeaking(false);
      alert("Unable to play AI voice. Please try again.");
    }
  };

  // Send question and receive AI answer
  const sendMessage = async (voiceQuestion = question) => {
  if (!voiceQuestion.trim() || loading) return;
    stopVoice();
const userQuestion = voiceQuestion.trim();

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: userQuestion
      }
    ]);

    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: userQuestion
        })
      });

      if (!response.ok) {
        throw new Error("Backend request failed.");
      }

      const data = await response.json();
      const cleanedAnswer = cleanResponse(data.answer);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: cleanedAnswer
        }
      ]);

      // Automatically speak the AI answer
      await playVoice(cleanedAnswer);

    } catch (error) {
      console.error("Chat error:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Unable to connect to the server. Please check your backend."
        }
      ]);

    } finally {
      setLoading(false);
    }
  };

  // Start a new conversation
  const newConversation = () => {
    stopVoice();

    setMessages([
      {
        role: "assistant",
        text: "Welcome back! What would you like to learn today?"
      }
    ]);

    setQuestion("");
  };

  return (
    <div className="app">

      <aside className="sidebar">
        <h2>⚡ PowerWise AI</h2>
        <p className="subtitle">Master the art of power</p>

        <button className="new-chat" onClick={newConversation}>
          + New Conversation
        </button>

        <h3>THE 48 LAWS</h3>

        <div className="law-list">
          {laws.map((law) => (
            <button
              key={law.law_number}
              className="law-item"
              onClick={() => setQuestion(`Explain Law ${law.law_number}`)}
            >
              <span>Law {law.law_number}</span>
              {law.title}
            </button>
          ))}
        </div>
      </aside>

      <main className="main">

        <header className="header">
          <div>
            <h1>PowerWise AI</h1>
            <p>Your intelligent power and strategy assistant</p>
          </div>

          <span className="status">● Online</span>
        </header>

        <section className="chat-area">

          <div className="welcome">
            <div className="brain">✦</div>
            <h2>Understand Power. Master Strategy.</h2>
            <p>
              Explore the 48 Laws of Power through intelligent conversations.
            </p>
          </div>

          <div className="messages">

            {messages.map((message, index) => (
              <div
                key={index}
                className={`message ${message.role}`}
              >
                <strong>
                  {message.role === "user" ? "You" : "PowerWise AI"}
                </strong>

                <p>{message.text}</p>
              </div>
            ))}

            {loading && (
              <div className="message assistant">
                <strong>PowerWise AI</strong>
                <p>Thinking...</p>
              </div>
            )}

          </div>
        </section>

        <div className="chat-input">

          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            placeholder="Ask about leadership, influence, strategy..."
          />

          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading}
          >
            {isRecording ? "⏹ Stop Recording" : "🎤 Speak"}
          </button>

          {isSpeaking && (
            <button onClick={stopVoice}>
              ⏹ Stop Voice
            </button>
          )}

          <button onClick={sendMessage} disabled={loading}>
            {loading ? "..." : "Send ➤"}
          </button>

        </div>

        <p className="footer">
          PowerWise AI • Your guide to strategic thinking
        </p>

      </main>
    </div>
  );
}

export default App;
