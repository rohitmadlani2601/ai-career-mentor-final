import streamlit as st
import os
import json
import time
from io import BytesIO
import datetime
import google.generativeai as genai
from google.cloud import speech
import PyPDF2

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="AI Career Mentor", page_icon="🎓", layout="wide")

# -------------------------
# Check API Key First
# -------------------------
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GENAI_API_KEY:
    st.error("❌ GOOGLE_API_KEY environment variable not set!")
    st.code("export GOOGLE_API_KEY='AIzaSyA6yLB-M5JgNK8PYT76NI_ES0YnhqS3hkU'")
    st.stop()

# -------------------------
# Configure Gemini
# -------------------------
try:
    genai.configure(api_key=GENAI_API_KEY)
    # Use correct model name - try gemini-1.5-flash or gemini-pro
    MODEL_NAME = "gemini-2.5-pro"
    st.sidebar.success(f"✅ Gemini API configured ({MODEL_NAME})")
except Exception as e:
    st.error(f"Failed to configure Gemini: {e}")
    st.stop()

# -------------------------
# Small CSS to make UI nicer
# -------------------------
st.markdown(
    """
    <style>
    .card { border: 1px solid #e6e9ee; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(32,33,36,0.06); background: #ffffff; }
    .card h3 { margin-bottom: 8px; }
    .primary-btn { background-color: #0f62fe; color: white; padding: 8px 14px; border-radius: 8px; border: none; }
    .small-muted { color: #6b7280; font-size: 13px; }
    .result-block { background: #f7fbff; padding: 12px; border-radius: 8px; }
    .progress-bar { background-color: #0f62fe; height: 12px; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Sidebar: user info + nav
# -------------------------
with st.sidebar:
    st.header("Welcome")
    user_name = st.text_input("Your name (optional)", value="")
    st.markdown("### Navigate")
    page = st.radio("", [
        "Dashboard",
        "Career Advice",
        "Job Suggestor",
        "Resume Evaluator",
        "Mock Interview",
        "Speech-to-Text",
        "Notifier",
        "Facial Analysis"
    ])
    st.markdown("---")
    st.write("Tip: Try the Mock Interview for quick practice.")

if user_name.strip():
    st.sidebar.info(f"Hi {user_name.split()[0]} — ready to upskill? 👋")


# -------------------------
# Utility helpers
# -------------------------
def download_text_button(text, filename="output.txt", label="Download"):
    b = text.encode("utf-8")
    st.download_button(label, b, file_name=filename, mime="text/plain")


# -------------------------
# Backend Logic (Functions with better error handling)
# -------------------------

def career_advice(profile):
    """Generate career advice using Gemini"""
    try:
        st.write("🔍 Generating advice with Gemini...")
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Act as a career advisor. 

User Profile: {profile}

Please provide:
1. Career path recommendations
2. Skills that should be learned
3. 30-day learning roadmap
4. Industry insights"""

        response = model.generate_content(prompt)

        if hasattr(response, 'text') and response.text:
            return {"advice": response.text}
        else:
            return {"error": "Empty response from Gemini"}

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error: {str(e)}")
        with st.expander("🔍 See error details"):
            st.code(error_details)
        return {"error": str(e)}


def job_suggestor(profile, location=""):
    """Suggest jobs using Gemini"""
    try:
        st.write("🔍 Finding suitable job roles...")
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""The user profile is: {profile}
Location preference: {location if location else "Any"}

Suggest 5 suitable job roles for this person.
For each role provide:
- Role name
- Short description (2-3 lines)
- Top 3-4 companies that hire for this role
- Companies currently hiring (2025)

Return ONLY a valid JSON array with this exact format:
[
  {{
    "role": "Job Role Name",
    "description": "Short description of the role",
    "companies": ["Company1", "Company2", "Company3"],
    "hiring_now": ["CompanyA", "CompanyB"]
  }}
]

Important: Return ONLY the JSON array, no markdown formatting, no extra text."""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text') or not response.text:
            return {"error": "Empty response from Gemini"}

        # Clean response text
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()

        try:
            jobs = json.loads(text)
            return {"jobs": jobs}
        except json.JSONDecodeError as je:
            st.warning("Could not parse JSON response, showing raw text")
            return {"jobs": text, "raw": True}

    except Exception as e:
        import traceback
        st.error(f"Error: {str(e)}")
        with st.expander("🔍 See error details"):
            st.code(traceback.format_exc())
        return {"error": str(e)}


def resume_eval(file):
    """Evaluate resume using Gemini"""
    try:
        st.write("📄 Extracting text from PDF...")
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return {"error": "Could not extract text from PDF"}

        st.write("🔍 Analyzing resume with Gemini...")
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Act as a professional career consultant and resume expert.

Analyze this resume and provide:

1. **Strengths** (3-5 points)
2. **Weaknesses** (3-5 points)
3. **Missing Skills** (specific technical and soft skills)
4. **Improvement Suggestions** (concrete, actionable advice)
5. **Overall Score** (out of 10)

Resume Text:
{text[:4000]}

Provide detailed, constructive feedback."""

        response = model.generate_content(prompt)

        if hasattr(response, 'text') and response.text:
            return {"evaluation": response.text}
        else:
            return {"error": "Empty response from Gemini"}

    except Exception as e:
        import traceback
        st.error(f"Error: {str(e)}")
        with st.expander("🔍 See error details"):
            st.code(traceback.format_exc())
        return {"error": str(e)}


def mock_interview(role):
    """Generate interview questions using Gemini"""
    if not role.strip():
        return {"error": "Role required"}

    try:
        st.write("🔍 Generating interview questions...")
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Generate 5 realistic interview questions for the role of: {role}

Return ONLY a JSON array of question strings, like this:
["Question 1 text here", "Question 2 text here", "Question 3 text here", "Question 4 text here", "Question 5 text here"]

Important: 
- Return ONLY the JSON array
- No markdown formatting
- No numbering in the questions themselves
- Each question should be realistic and specific to the role"""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text') or not response.text:
            return {"error": "Empty response from Gemini"}

        # Clean response
        import re
        raw_text = response.text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'^```\s*', '', raw_text)
        raw_text = re.sub(r'```\s*$', '', raw_text)
        raw_text = raw_text.strip()

        try:
            questions = json.loads(raw_text)
            if isinstance(questions, list):
                questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
                return {"questions": questions}
            else:
                # Fallback: split by newlines
                questions = [q.strip() for q in raw_text.split('\n') if q.strip()]
                return {"questions": questions[:5]}
        except:
            # Last resort: split by newlines
            questions = [q.strip('- •123456789.') for q in raw_text.split('\n') if q.strip()]
            return {"questions": questions[:5]}

    except Exception as e:
        import traceback
        st.error(f"Error: {str(e)}")
        with st.expander("🔍 See error details"):
            st.code(traceback.format_exc())
        return {"error": str(e)}


def evaluate_answer(question, transcript, resume_text=""):
    """Evaluate interview answer using Gemini"""
    if not transcript.strip():
        return {"error": "No answer provided"}

    try:
        st.write("🔍 Evaluating your answer...")
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""You are an expert HR interviewer evaluating a candidate's answer.

Question: {question}

Candidate's Answer: {transcript}

Resume Context: {resume_text[:500] if resume_text else "Not provided"}

Evaluate the answer and provide a JSON response with these exact fields:
{{
  "clarity": 7,
  "confidence": 8,
  "score": 7.5,
  "feedback": "Detailed feedback text here explaining strengths and areas for improvement"
}}

Scoring guide:
- clarity: 0-10 (how clear and structured the answer is)
- confidence: 0-10 (estimated confidence level based on language used)
- score: 0-10 (overall answer quality)
- feedback: Detailed constructive feedback (3-5 sentences)

Return ONLY the JSON object, no markdown formatting."""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text') or not response.text:
            return {"error": "Empty response from Gemini"}

        # Clean and parse JSON
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()

        try:
            eval_json = json.loads(text)
            return eval_json
        except:
            # Fallback: extract what we can
            return {
                "clarity": 5,
                "confidence": 5,
                "score": 5,
                "feedback": response.text
            }

    except Exception as e:
        import traceback
        st.error(f"Error: {str(e)}")
        with st.expander("🔍 See error details"):
            st.code(traceback.format_exc())
        return {"error": str(e)}


def speech_to_text(audio_file):
    """Transcribe audio using Google Cloud Speech-to-Text"""
    try:
        audio_content = audio_file.read()
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        transcript = " ".join([r.alternatives[0].transcript for r in response.results])
        return {"text": transcript}
    except Exception as e:
        return {"error": str(e)}


# -------------------------
# Streamlit Pages
# -------------------------

if page == "Dashboard":
    st.title("🎓 AI Career Mentor — Dashboard")
    greeting = f"Welcome back, {user_name.split()[0]}!" if user_name.strip() else "Welcome to your Career Mentor"
    st.markdown(f"#### {greeting}")
    st.markdown(
        "This dashboard helps with career choices, resume review, interview practice, and daily learning nudges.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="card"><h3>Career Advice</h3><p class="small-muted">Personalized career paths & 30-day roadmap</p></div>',
            unsafe_allow_html=True)
    with col2:
        st.markdown(
            '<div class="card"><h3>Mock Interview</h3><p class="small-muted">Practice Q&A + feedback on clarity & confidence</p></div>',
            unsafe_allow_html=True)
    with col3:
        st.markdown(
            '<div class="card"><h3>Resume Evaluator</h3><p class="small-muted">Get strengths, weaknesses & improvement tips</p></div>',
            unsafe_allow_html=True)

elif page == "Career Advice":
    st.header("🧭 Personalized Career Advice")
    profile = st.text_area("Describe your profile (education, skills, interests, goals):", height=180)

    if st.button("Get Advice", key="get_advice"):
        if not profile.strip():
            st.warning("Please enter your profile so I can give tailored advice.")
        else:
            with st.spinner("Generating personalized career advice..."):
                resp = career_advice(profile)

                if "error" in resp:
                    st.error(f"Error: {resp['error']}")
                else:
                    advice = resp.get("advice", "")
                    st.markdown("### Results")
                    st.markdown(f"<div class='result-block'>{advice}</div>", unsafe_allow_html=True)
                    download_text_button(advice, filename="career_advice.txt", label="Download Advice")

elif page == "Job Suggestor":
    st.header("💼 Job Suggestor")
    profile = st.text_area("Enter your profile (skills, domain, interests):", height=140)
    location = st.text_input("Preferred location (optional)")

    if st.button("Suggest Jobs", key="suggest_jobs"):
        if not profile.strip():
            st.warning("Please provide at least a short profile or skills.")
        else:
            with st.spinner("Finding best-fit job roles..."):
                resp = job_suggestor(profile, location)

                if "error" in resp:
                    st.error(f"Error: {resp['error']}")
                elif "raw" in resp:
                    st.markdown("**Job Suggestions:**")
                    st.text(resp.get("jobs", ""))
                else:
                    jobs = resp.get("jobs", [])
                    if isinstance(jobs, list):
                        for i, j in enumerate(jobs):
                            st.markdown(f"### 🔹 {j.get('role', 'N/A')}")
                            st.markdown(j.get("description", ""))

                            companies = j.get("companies", [])
                            if companies:
                                st.markdown("**Recommended companies:** " + ", ".join(companies))

                            hiring = j.get("hiring_now", [])
                            if hiring:
                                st.success("📌 Companies hiring now: " + ", ".join(hiring))
                            st.divider()

elif page == "Resume Evaluator":
    st.header("📄 Resume Evaluator")
    st.markdown(
        "Upload your resume (PDF). The system will extract text and provide strengths, weaknesses, missing skills and concrete improvements.")

    resume_file = st.file_uploader("Upload PDF resume", type=["pdf"])

    if resume_file:
        if st.button("Evaluate Resume", key="eval_resume"):
            with st.spinner("Extracting and evaluating resume..."):
                resp = resume_eval(resume_file)

                if "error" in resp:
                    st.error(f"Error: {resp['error']}")
                else:
                    ev = resp.get("evaluation", "")
                    st.markdown("### Resume Evaluation")
                    st.markdown(ev)
                    st.success("Evaluation complete.")
                    download_text_button(ev, filename="resume_evaluation.txt", label="Download Evaluation")

elif page == "Mock Interview":
    st.header("🎤 Mock Interview")
    role = st.text_input("Role to prepare for (e.g., Embedded Systems Engineer):")
    start = st.button("Start Mock Interview", key="start_mock")

    if "mi_questions" not in st.session_state:
        st.session_state.mi_questions = []
    if "mi_idx" not in st.session_state:
        st.session_state.mi_idx = 0
    if "mi_results" not in st.session_state:
        st.session_state.mi_results = []

    if start:
        if not role.strip():
            st.warning("Please enter the role.")
        else:
            with st.spinner("Generating interview questions..."):
                resp = mock_interview(role)

                if "error" in resp:
                    st.error(f"Error: {resp['error']}")
                else:
                    questions = resp.get("questions", [])
                    if isinstance(questions, list) and questions:
                        st.session_state.mi_questions = questions
                        st.session_state.mi_idx = 0
                        st.session_state.mi_results = []
                        st.success(f"Generated {len(questions)} questions!")
                    else:
                        st.warning("No questions generated. Try again.")

    if st.session_state.mi_questions:
        idx = st.session_state.mi_idx
        current_question = st.session_state.mi_questions[idx]

        st.subheader(f"Question {idx + 1} of {len(st.session_state.mi_questions)}")
        st.markdown(f"**{current_question}**")

        answer = st.text_area(
            "Type your answer here:",
            key=f"ans_{idx}",
            height=150
        )

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("Submit Answer", key=f"submit_{idx}"):
                if not answer.strip():
                    st.warning("Please type an answer.")
                else:
                    with st.spinner("Evaluating answer..."):
                        res = evaluate_answer(current_question, answer)

                        if "error" in res:
                            st.error(f"Error: {res['error']}")
                        else:
                            st.session_state.mi_results.append(res)
                            st.success("Answer evaluated!")
                            if idx + 1 < len(st.session_state.mi_questions):
                                st.session_state.mi_idx += 1
                                st.rerun()

        with col2:
            if st.button("Skip / Next", key=f"next_{idx}"):
                if idx + 1 < len(st.session_state.mi_questions):
                    st.session_state.mi_idx += 1
                    st.rerun()

        with col3:
            if st.button("Finish Interview", key="finish_mock"):
                st.session_state.mi_idx = 0
                st.session_state.mi_questions = []
                st.session_state.mi_results = []
                st.success("Mock interview ended.")
                st.rerun()

        if st.session_state.mi_results:
            st.markdown("### Previous Answers & Feedback")
            for i, r in enumerate(st.session_state.mi_results):
                st.markdown(f"**Q{i + 1}:** {st.session_state.mi_questions[i]}")
                st.markdown(f"- **Clarity:** {r.get('clarity', 'N/A')}/10")
                st.markdown(f"- **Confidence:** {r.get('confidence', 'N/A')}/10")
                st.markdown(f"- **Score:** {r.get('score', 'N/A')}/10")
                st.markdown(f"- **Feedback:** {r.get('feedback', '')}")
                st.divider()

elif page == "Speech-to-Text":
    st.header("🗣️ Speech to Text")
    st.markdown("Upload a WAV audio file for transcription.")
    st.info("Note: Requires Google Cloud credentials to be configured")

    audio_file = st.file_uploader("Upload audio file (wav)", type=["wav"])

    if audio_file and st.button("Transcribe Audio"):
        with st.spinner("Transcribing..."):
            resp = speech_to_text(audio_file)

            if "error" in resp:
                st.error(f"Error: {resp['error']}")
            else:
                text = resp.get("text", "")
                st.success("Transcription complete")
                st.markdown("**Transcript:**")
                st.write(text)
                download_text_button(text, filename="transcript.txt", label="Download Transcript")

elif page == "Notifier":
    st.header("🔔 Notifier (Reminders)")
    st.warning(
        "⚠️ This feature requires a backend service with APScheduler running continuously. It won't work in standalone Streamlit mode.")
    st.info("Consider using external services like Google Calendar API or scheduling services for production use.")

elif page == "Facial Analysis":
    st.header("📹 Facial Expression Evaluator")
    st.info(
        "💡 Coming soon - will analyze facial expressions during mock interviews to provide feedback on non-verbal communication")

st.markdown("---")
st.markdown("<div class='small-muted'>💡 Tip: Use download buttons to save your outputs for later reference.</div>",
            unsafe_allow_html=True)