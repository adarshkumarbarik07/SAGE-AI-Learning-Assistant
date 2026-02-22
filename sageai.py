import streamlit as st
import requests
from PyPDF2 import PdfReader
from gtts import gTTS
from io import BytesIO
import base64
import re

# ────────────────────────────────────────────────
# CONFIG – GROQ (BEST FREE-FOREVER)
# ────────────────────────────────────────────────
# Insert your API key here before running
API_KEY = "YOUR_API_KEY"
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"  # Fast & free

st.set_page_config(page_title="SAGE ai", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ────────────────────────────────────────────────
# CSS – Clean & modern
# ────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0a0a1f 0%, #1a0b3d 50%, #2a1b5f 100%);
    }
    .neon-title {
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(90deg, #c026d3, #7c3aed, #22d3ee);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 40px rgba(139,92,246,0.7);
        text-align: center;
    }
    .glass-card {
        background: rgba(255,255,255,0.07);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(139,92,246,0.3);
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .user-message {
        background: rgba(30,41,59,0.9);
        color: #e0e7ff;
        padding: 16px 24px;
        border-radius: 18px 18px 4px 18px;
        margin: 12px 0 12px auto;
        max-width: 75%;
        border: 1px solid rgba(100,100,255,0.3);
    }
    .ai-message {
        background: linear-gradient(135deg, rgba(124,58,237,0.25), rgba(192,38,211,0.2));
        color: #e0e7ff;
        padding: 16px 24px;
        border-radius: 18px 18px 18px 4px;
        margin: 12px 0 12px 0;
        max-width: 75%;
        border-left: 5px solid #8b5cf6;
    }
    .listen-btn {
        background: #6366f1 !important;
        color: white !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 1.3rem !important;
        margin-top: 8px !important;
    }
    .stop-btn {
        background: #ef4444 !important;
        color: white !important;
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        margin-top: 8px !important;
    }
    .source-tag {
        font-size: 0.85rem;
        color: #a5b4fc;
        margin-top: 8px;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if "messages" not in st.session_state: st.session_state.messages = []
if "syllabus" not in st.session_state: st.session_state.syllabus = ""
if "syllabus_chunks" not in st.session_state: st.session_state.syllabus_chunks = []
if "mode" not in st.session_state: st.session_state.mode = "Quick"
if "audio_src" not in st.session_state: st.session_state.audio_src = None

# ────────────────────────────────────────────────
# CLEANING & RAG FUNCTIONS
# ────────────────────────────────────────────────
def clean_text(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def read_pdf(file):
    text = ""
    try:
        pdf = PdfReader(file)
        for page in pdf.pages:
            txt = page.extract_text()
            if txt: text += txt + "\n"
        return clean_text(text)
    except:
        return ""

def read_txt(file):
    try:
        return clean_text(file.read().decode("utf-8", errors="replace"))
    except:
        return ""

def get_relevant_chunks(question, chunks):
    if not chunks: return []
    q = question.lower()
    scored = sorted([(sum(1 for w in q.split() if len(w)>3 and w in c.lower()), c) for c in chunks], reverse=True)
    return [c for _, c in scored[:5]]  # Return only chunks (fixed)

def clean_for_speech(text):
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*{1,2}|`{1,3}', '', text)
    text = re.sub(r'[-*+>]\s*', ' ', text)
    text = re.sub(r'Confidence:.*|Source:.*', '', text, flags=re.I)
    return ' '.join(text.split())

# ────────────────────────────────────────────────
# VOICE – gTTS (reliable) + manual stop
# ────────────────────────────────────────────────
def speak(text, message_id):
    clean_text = clean_for_speech(text)
    try:
        with st.spinner("Preparing voice..."):
            tts = gTTS(text=clean_text, lang="en")
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            b64 = base64.b64encode(fp.read()).decode()
            audio_src = f"data:audio/mp3;base64,{b64}"
        st.session_state.audio_src = audio_src
        st.rerun()
    except Exception as e:
        st.error(f"Voice failed: {e}")
        st.session_state.audio_src = None

def stop_audio():
    st.session_state.audio_src = None
    st.rerun()

# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h1 class="neon-title">SAGE.ai</h1>', unsafe_allow_html=True)
    st.markdown('<p class="neon-subtitle">Your Personal AI Learning Companion</p>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card"><div style="background:#22c55e;color:#fff;padding:8px 16px;border-radius:999px;display:inline-block;font-size:0.9rem;font-weight:600;">Powered by NEURAL TITANS</div></div>', unsafe_allow_html=True)

    st.subheader("📤 Upload Syllabus")
    files = st.file_uploader("", type=["pdf","txt"], accept_multiple_files=True, label_visibility="collapsed")
    if files:
        full = ""
        for f in files:
            if f.name.lower().endswith(".pdf"):
                full += read_pdf(f) + "\n\n"
            else:
                full += read_txt(f) + "\n\n"
        st.session_state.syllabus = full.strip()
        st.session_state.syllabus_chunks = [full[i:i+1800] for i in range(0, len(full), 1600)]
        st.success(f"Loaded {len(files)} file(s) • Ready for questions")

    st.subheader("⚡ Answer Style")
    mode_options = ["Quick", "Step-by-Step", "Exam Ready"]
    selected_mode = st.selectbox("", mode_options, index=mode_options.index(st.session_state.mode))
    st.session_state.mode = selected_mode

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.audio_src = None
        st.rerun()

# ────────────────────────────────────────────────
# TABS – Chat + MCQ + Mind Map
# ────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Chat", "🧠 Practice MCQs", "🗺️ Mind Map"])

with tab1:
    st.markdown('<h2 style="color:#c4b5fd;text-align:center;">Ask Anything from Syllabus</h2>', unsafe_allow_html=True)

    for i, (role, msg) in enumerate(st.session_state.messages):
        if role == "user":
            st.markdown(f'<div class="user-message">👤 {msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-message">🤖 {msg}</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([7, 3])
            with col1:
                if st.button("🔊 Listen", key=f"voice_{i}"):
                    speak(msg, i)
                    st.rerun()
            with col2:
                if st.session_state.audio_src is not None:
                    if st.button("⏹ Stop", key=f"stop_{i}"):
                        stop_audio()
                        st.rerun()

    if st.session_state.audio_src:
        st.audio(st.session_state.audio_src, format="audio/mp3")

with tab2:
    st.header("Practice with MCQs")
    st.caption("Generate exam-style questions from your syllabus")
    if st.button("Generate 5 New MCQs", type="primary", use_container_width=True):
        with st.spinner("Creating questions..."):
            # FIXED: No unpacking needed
            if not st.session_state.syllabus_chunks:
                st.warning("No syllabus content loaded yet.")
            else:
                context = "\n\n".join(st.session_state.syllabus_chunks[:5])
                prompt = f"""Generate 5 high-quality multiple-choice questions (4 options each) with correct answer marked and short explanation.
Use ONLY this syllabus content:
{context}"""
                try:
                    r = requests.post(
                        API_URL,
                        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.7,
                            "max_tokens": 1200
                        },
                        timeout=60
                    )
                    r.raise_for_status()
                    mcqs = r.json()["choices"][0]["message"]["content"].strip()
                    st.markdown(mcqs)
                except Exception as e:
                    st.error(f"Failed to generate MCQs: {str(e)}")

with tab3:
    st.header("Syllabus Mind Map")
    st.caption("Visual summary of main topics & subtopics")
    if st.button("Generate Mind Map", type="primary", use_container_width=True):
        with st.spinner("Creating mind map..."):
            # FIXED: No unpacking needed
            if not st.session_state.syllabus_chunks:
                st.warning("No syllabus content loaded yet.")
            else:
                context = "\n\n".join(st.session_state.syllabus_chunks[:5])
                prompt = f"""Create a clean text-based mind map (markdown tree format) summarizing the main topics, subtopics and key points from this syllabus content:
{context}

Use format like:
- Main Topic 1
  - Subtopic A
    - Key point
  - Subtopic B
- Main Topic 2
..."""
                try:
                    r = requests.post(
                        API_URL,
                        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.5,
                            "max_tokens": 1000
                        },
                        timeout=60
                    )
                    r.raise_for_status()
                    mindmap = r.json()["choices"][0]["message"]["content"].strip()
                    st.markdown(mindmap)
                except Exception as e:
                    st.error(f"Failed to generate mind map: {str(e)}")

# ────────────────────────────────────────────────
# CHAT INPUT
# ────────────────────────────────────────────────
question = st.chat_input("Ask your doubt from the syllabus...")

if question:
    if not st.session_state.syllabus:
        st.error("Please upload your syllabus first!")
    else:
        st.session_state.messages.append(("user", question))
        with st.spinner("Searching syllabus..."):
            relevant = get_relevant_chunks(question, st.session_state.syllabus_chunks)
            context = "\n\n---\n\n".join(relevant)  # FIXED: relevant is now list of strings
            sources = []  # No scores anymore, so empty or customize if needed

            system_prompt = f"""You are SAGE ai — strict syllabus-only tutor.
Answer ONLY from the context. Never hallucinate or use external knowledge.
If not found → "Sorry, this topic is not covered in the uploaded syllabus."
Be clear, student-friendly, use simple Hinglish if question is in Hindi.
Mode: {st.session_state.mode}
- Quick: short direct answer
- Step-by-Step: numbered clear steps
- Exam Ready: formal, keyword-rich, exam-style
Always end with:
Confidence: High / Medium / Low
Source: {', '.join(sources) if sources else 'General context'}
Context:
{context}"""

            try:
                r = requests.post(
                    API_URL,
                    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": MODEL,
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
                        "temperature": 0.3,
                        "max_tokens": 1200
                    },
                    timeout=60
                )
                r.raise_for_status()
                answer = r.json()["choices"][0]["message"]["content"].strip()
                st.session_state.messages.append(("assistant", answer))
            except Exception as e:
                st.session_state.messages.append(("assistant", f"⚠️ Error: {str(e)}"))
        st.rerun()