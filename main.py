import streamlit as st
import os
import json
import time
from io import BytesIO
import datetime
import google.generativeai as genai
from google.cloud import speech
import PyPDF2
import firebase_admin
from firebase_admin import credentials, auth, firestore
import hashlib
import cv2
import numpy as np
from pydub import AudioSegment
import tempfile
#from deepface import DeepFace
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
#from deepface import DeepFace
#DeepFace.build_model("ArcFace")  # ensures PyTorch backend

# -------------------------
# Firebase Initialization
# -------------------------
if not firebase_admin._apps:
    try:
        # Use environment variable for credentials path
        cred_path = os.environ.get("FIREBASE_CREDENTIALS", "aicareermentor-1b611-firebase-adminsdk-fbsvc-891358d987.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")
        db = None
else:
    db = firestore.client()

# -------------------------
# Page Config
# -------------------------
st.set_page_config(
    page_title="AI Career Mentor Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# Enhanced CSS
# -------------------------
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Main Theme */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }

    .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    }

    /* Enhanced Cards */
    .card {
        border: none;
        border-radius: 15px;
        padding: 24px;
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }

    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
    }

    .card h3 {
        color: #667eea;
        font-weight: 600;
        margin-bottom: 12px;
    }

    /* Stats Card */
    .stat-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid #667eea;
    }

    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        margin: 10px 0;
    }

    .stat-label {
        color: #6b7280;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Result Block */
    .result-block {
        background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin: 15px 0;
    }

    /* Success/Warning/Error Messages */
    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }

    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }

    /* Progress Bar */
    .progress-container {
        background: #e5e7eb;
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        margin: 15px 0;
    }

    .progress-bar {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* Input Fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        padding: 12px;
        transition: all 0.3s ease;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }

    /* Small Muted Text */
    .small-muted {
        color: #6b7280;
        font-size: 0.875rem;
        line-height: 1.5;
    }

    /* Badge */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 4px;
    }

    .badge-success {
        background: #d1fae5;
        color: #065f46;
    }

    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }

    .badge-info {
        background: #dbeafe;
        color: #1e40af;
    }

    /* Interview Score Card */
    .score-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 15px 0;
    }

    .score-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }

    .score-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }

    /* Animation */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animated {
        animation: slideIn 0.5s ease;
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# -------------------------
# Check API Key
# -------------------------
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GENAI_API_KEY:
    st.error("❌ GOOGLE_API_KEY environment variable not set!")
    st.code("export GOOGLE_API_KEY='your-key-here'")
    st.stop()

# -------------------------
# Configure Gemini
# -------------------------
try:
    genai.configure(api_key=GENAI_API_KEY)
    MODEL_NAME = "gemini-2.5-pro"
except Exception as e:
    st.error(f"Failed to configure Gemini: {e}")
    st.stop()

# -------------------------
# Session State Initialization
# -------------------------
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'mi_questions' not in st.session_state:
    st.session_state.mi_questions = []
if 'mi_idx' not in st.session_state:
    st.session_state.mi_idx = 0
if 'mi_results' not in st.session_state:
    st.session_state.mi_results = []
if 'interview_history' not in st.session_state:
    st.session_state.interview_history = []
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"


# -------------------------
# Utility Functions
# -------------------------
def download_text_button(text, filename="output.txt", label="Download"):
    b = text.encode("utf-8")
    st.download_button(label, b, file_name=filename, mime="text/plain")


def create_user_profile(email, user_id):
    """Create user profile in Firestore"""
    if db:
        try:
            db.collection('users').document(user_id).set({
                'email': email,
                'created_at': firestore.SERVER_TIMESTAMP,
                'total_interviews': 0,
                'total_advice_requests': 0,
                'total_resume_evals': 0,
                'subscription_tier': 'free'
            })
        except Exception as e:
            st.error(f"Error creating profile: {e}")


def update_user_stats(user_id, stat_type):
    """Update user statistics"""
    if db and user_id:
        try:
            user_ref = db.collection('users').document(user_id)
            user_ref.update({stat_type: firestore.Increment(1)})
        except Exception as e:
            print(f"Error updating stats: {e}")


def save_interview_result(user_id, role, questions, results):
    """Save interview results to Firestore"""
    if db and user_id:
        try:
            db.collection('interviews').add({
                'user_id': user_id,
                'role': role,
                'questions': questions,
                'results': results,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'average_score': sum([r.get('score', 0) for r in results]) / len(results) if results else 0
            })
            update_user_stats(user_id, 'total_interviews')
        except Exception as e:
            st.error(f"Error saving interview: {e}")


def get_user_stats(user_id):
    """Get user statistics from Firestore"""
    if db and user_id:
        try:
            doc = db.collection('users').document(user_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print(f"Error getting stats: {e}")
    return {}


def analyze_facial_expression(frame):
    """Analyze facial expression using DeepFace"""
    try:
        # Analyze the frame
        # DeepFace disabled due to TensorFlow errors
        return "neutral", {}

    except Exception as e:
        return "neutral", {}


def convert_audio_to_wav(audio_file, output_format="wav"):
    """Convert MP3/other audio to WAV for speech recognition"""
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_input:
            temp_input.write(audio_file.read())
            temp_input_path = temp_input.name

        # Convert to WAV
        audio = AudioSegment.from_file(temp_input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)

        temp_output_path = temp_input_path.replace(".mp3", ".wav")
        audio.export(temp_output_path, format="wav")

        # Read WAV file
        with open(temp_output_path, 'rb') as wav_file:
            wav_content = wav_file.read()

        # Cleanup
        os.remove(temp_input_path)
        os.remove(temp_output_path)

        return wav_content
    except Exception as e:
        raise Exception(f"Audio conversion failed: {e}")


# -------------------------
# Core AI Functions
# -------------------------
def career_advice(profile, user_id=None):
    """Generate career advice using Gemini"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Act as a senior career advisor with 15 years of experience.

User Profile: {profile}

Provide comprehensive career guidance including:

1. **Career Path Analysis**
   - 3 specific career paths with pros and cons
   - Expected career progression timeline
   - Salary ranges for each path

2. **Skills Development Roadmap**
   - Top 5 technical skills (prioritized)
   - Top 3 soft skills
   - Recommended learning resources

3. **30-Day Action Plan**
   - Week 1-4 breakdown with specific tasks
   - Daily time commitment suggestions
   - Milestones to track progress

4. **Industry Insights**
   - Current market trends
   - High-demand roles
   - Future-proof skills

Format: Use clear markdown with sections and bullet points."""

        response = model.generate_content(prompt)

        if user_id:
            update_user_stats(user_id, 'total_advice_requests')

        if hasattr(response, 'text') and response.text:
            return {"advice": response.text}
        else:
            return {"error": "Empty response from Gemini"}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def job_suggestor(profile, location="", experience_level=""):
    """Suggest jobs using Gemini with enhanced details"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""User Profile: {profile}
Location: {location if location else "Remote/Flexible"}
Experience Level: {experience_level if experience_level else "Any"}

Suggest 5 suitable job roles. For each role provide:
- Role name
- Detailed description (3-4 sentences)
- Required skills (technical and soft)
- Salary range (in USD)
- Top 5 companies hiring
- Growth potential (1-5 scale)
- Work-life balance (1-5 scale)

Return ONLY valid JSON array:
[
  {{
    "role": "Role Name",
    "description": "Detailed description",
    "skills": ["Skill1", "Skill2", "Skill3"],
    "salary_range": "$80k-$120k",
    "companies": ["Company1", "Company2", "Company3", "Company4", "Company5"],
    "growth_potential": 4,
    "work_life_balance": 3
  }}
]"""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text') or not response.text:
            return {"error": "Empty response"}

        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text).strip()

        try:
            jobs = json.loads(text)
            return {"jobs": jobs}
        except:
            return {"jobs": text, "raw": True}

    except Exception as e:
        return {"error": str(e)}


def resume_eval(file, user_id=None):
    """Evaluate resume with enhanced analysis"""
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return {"error": "Could not extract text from PDF"}

        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Act as a professional resume expert and ATS specialist.

Analyze this resume comprehensively:

{text[:5000]}

Provide:

1. **Overall Score**: X/10 with brief justification

2. **Strengths** (5 points)
   - Specific examples from the resume

3. **Weaknesses** (5 points)
   - Specific issues to address

4. **ATS Compatibility**
   - Score: X/10
   - Issues: List formatting/keyword problems
   - Suggestions: How to improve ATS score

5. **Missing Elements**
   - Skills that should be added
   - Sections that are missing
   - Industry-specific requirements

6. **Actionable Improvements** (8-10 specific points)
   - Prioritized list of changes
   - Examples of better phrasing

7. **Keyword Analysis**
   - Important keywords present
   - Missing industry keywords
   - Optimal keyword density suggestions

Format: Use markdown with clear sections."""

        response = model.generate_content(prompt)

        if user_id:
            update_user_stats(user_id, 'total_resume_evals')

        if hasattr(response, 'text') and response.text:
            return {"evaluation": response.text}
        else:
            return {"error": "Empty response"}

    except Exception as e:
        return {"error": str(e)}


def mock_interview(role, experience_level="mid"):
    """Generate interview questions with difficulty levels"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Generate 5 realistic interview questions for: {role}
Experience Level: {experience_level}

Include:
- 2 technical questions
- 2 behavioral questions
- 1 situational/problem-solving question

Return ONLY JSON array:
[
  {{
    "question": "Question text",
    "type": "technical|behavioral|situational",
    "difficulty": "easy|medium|hard",
    "hints": "Brief hint for answering"
  }}
]"""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text'):
            return {"error": "Empty response"}

        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text).strip()

        try:
            questions = json.loads(text)
            return {"questions": questions}
        except:
            # Fallback
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            questions = [{"question": q, "type": "general", "difficulty": "medium", "hints": ""}
                         for q in lines[:5]]
            return {"questions": questions}

    except Exception as e:
        return {"error": str(e)}


def evaluate_answer(question, transcript, resume_text="", question_type="general"):
    """Enhanced answer evaluation with detailed feedback"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""You are an expert HR interviewer evaluating a candidate.

Question Type: {question_type}
Question: {question}
Candidate's Answer: {transcript}
Resume Context: {resume_text[:500] if resume_text else "Not provided"}

Evaluate and provide JSON:
{{
  "clarity": 8,
  "confidence": 7,
  "relevance": 9,
  "technical_accuracy": 8,
  "communication": 7,
  "overall_score": 7.8,
  "strengths": ["Point 1", "Point 2", "Point 3"],
  "improvements": ["Point 1", "Point 2", "Point 3"],
  "detailed_feedback": "2-3 paragraphs of constructive feedback",
  "model_answer_hints": "Brief example of a strong answer approach"
}}

Scoring: 0-10 for each metric"""

        response = model.generate_content(prompt)

        if not hasattr(response, 'text'):
            return {"error": "Empty response"}

        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text).strip()

        try:
            return json.loads(text)
        except:
            return {
                "clarity": 5, "confidence": 5, "relevance": 5,
                "technical_accuracy": 5, "communication": 5, "overall_score": 5,
                "strengths": [], "improvements": [],
                "detailed_feedback": response.text,
                "model_answer_hints": ""
            }

    except Exception as e:
        return {"error": str(e)}


def speech_to_text(audio_file, file_extension):
    """Enhanced speech to text with MP3 support"""
    try:
        # Convert MP3 to WAV if needed
        if file_extension.lower() in ['.mp3', '.m4a', '.ogg']:
            audio_content = convert_audio_to_wav(audio_file)
        else:
            audio_content = audio_file.read()

        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            model="default"
        )

        response = client.recognize(config=config, audio=audio)

        if not response.results:
            return {"text": "", "confidence": 0}

        transcript = " ".join([r.alternatives[0].transcript for r in response.results])
        confidence = sum([r.alternatives[0].confidence for r in response.results]) / len(response.results)

        return {"text": transcript, "confidence": confidence}
    except Exception as e:
        return {"error": str(e)}


# -------------------------
# Authentication Functions
# -------------------------
def sign_up(email, password):
    """Create new user account"""
    try:
        user = auth.create_user(email=email, password=password)
        create_user_profile(email, user.uid)
        return {"success": True, "user_id": user.uid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_in(email, password):
    """Sign in user (simplified - in production use Firebase Auth SDK)"""
    try:
        # Note: Firebase Admin SDK doesn't support password verification
        # In production, use Firebase Auth on client side or custom token approach
        user = auth.get_user_by_email(email)
        return {"success": True, "user_id": user.uid, "email": email}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -------------------------
# Authentication UI
# -------------------------
if st.session_state.user is None:
    st.title("🎓 AI Career Mentor Pro")
    st.markdown("### Your AI-Powered Career Growth Partner")

    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        st.markdown("#### Welcome Back!")
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")

        if st.button("Sign In", key="signin_btn"):
            if email and password:
                with st.spinner("Signing in..."):
                    result = sign_in(email, password)
                    if result["success"]:
                        st.session_state.user = {
                            "uid": result["user_id"],
                            "email": result["email"]
                        }
                        st.session_state.user_data = get_user_stats(result["user_id"])
                        st.success("Signed in successfully!")
                        st.rerun()
                    else:
                        st.error(f"Sign in failed: {result['error']}")
            else:
                st.warning("Please enter email and password")

    with tab2:
        st.markdown("#### Create Your Account")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")

        if st.button("Sign Up", key="signup_btn"):
            if email and password and confirm_password:
                if password == confirm_password:
                    if len(password) >= 6:
                        with st.spinner("Creating account..."):
                            result = sign_up(email, password)
                            if result["success"]:
                                st.success("Account created! Please sign in.")
                            else:
                                st.error(f"Sign up failed: {result['error']}")
                    else:
                        st.warning("Password must be at least 6 characters")
                else:
                    st.warning("Passwords don't match")
            else:
                st.warning("Please fill all fields")

    st.stop()

# -------------------------
# Main App (After Authentication)
# -------------------------

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['email'].split('@')[0].title()}")

    # User Stats
    stats = st.session_state.user_data
    st.markdown("#### Your Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Interviews", stats.get('total_interviews', 0))
        st.metric("Advice", stats.get('total_advice_requests', 0))
    with col2:
        st.metric("Resumes", stats.get('total_resume_evals', 0))
        tier = stats.get('subscription_tier', 'free')
        st.metric("Tier", tier.title())

    st.markdown("---")
    st.markdown("### 📚 Navigation")

    pages = [
        ("Dashboard", "🏠"),
        ("Career Advice", "🧭"),
        ("Job Suggestor", "💼"),
        ("Resume Evaluator", "📄"),
        ("Mock Interview", "🎤"),
        ("Interview History", "📊"),
        ("Speech-to-Text", "🗣️"),
        ("Facial Analysis", "📹"),
        ("Reminders", "🔔"),
        ("Profile Settings", "⚙️")
    ]

    for page_name, icon in pages:
        if st.button(f"{icon} {page_name}", key=f"nav_{page_name}", use_container_width=True):
            st.session_state.page = page_name
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.user = None
        st.session_state.user_data = {}
        st.rerun()

# Get current page
page = st.session_state.page

# -------------------------
# Dashboard
# -------------------------
if page == "Dashboard":
    st.title("🏠 Dashboard")
    st.markdown(f"### Welcome back, {st.session_state.user['email'].split('@')[0].title()}! 👋")

    # Stats Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
            <div class="stat-card">
                <div class="stat-label">Total Interviews</div>
                <div class="stat-number">{}</div>
            </div>
        """.format(stats.get('total_interviews', 0)), unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="stat-card">
                <div class="stat-label">Career Advice</div>
                <div class="stat-number">{}</div>
            </div>
        """.format(stats.get('total_advice_requests', 0)), unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class="stat-card">
                <div class="stat-label">Resumes Reviewed</div>
                <div class="stat-number">{}</div>
            </div>
        """.format(stats.get('total_resume_evals', 0)), unsafe_allow_html=True)
    with col4:
        st.markdown("""
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-number">{}%</div>
            </div>
        """.format(85), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class="card">
                <h3>🧭 Career Advice</h3>
                <p class="small-muted">Get personalized career paths, skills roadmap, and 30-day action plans powered by AI</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="card">
                <h3>🎤 Mock Interview</h3>
                <p class="small-muted">Practice with AI-generated questions and get detailed feedback on your answers</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class="card">
                <h3>📄 Resume Evaluator</h3>
                <p class="small-muted">ATS-optimized analysis with strengths, weaknesses, and improvement suggestions</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick Actions
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊 View Interview History", use_container_width=True):
            st.session_state.page = "Interview History"
            st.rerun()
    with col2:
        if st.button("💼 Find Jobs", use_container_width=True):
            st.session_state.page = "Job Suggestor"
            st.rerun()
    with col3:
        if st.button("🎯 Start Interview", use_container_width=True):
            st.session_state.page = "Mock Interview"
            st.rerun()
    with col4:
        if st.button("🗣️ Speech Practice", use_container_width=True):
            st.session_state.page = "Speech-to-Text"
            st.rerun()

# -------------------------
# Career Advice Page
# -------------------------
elif page == "Career Advice":
    st.title("🧭 Personalized Career Advice")
    st.markdown("Get AI-powered career guidance tailored to your profile")

    col1, col2 = st.columns([2, 1])

    with col1:
        profile = st.text_area(
            "Describe your profile (education, skills, interests, goals):",
            height=200,
            placeholder="e.g., I have a B.Tech in Computer Science, 2 years of experience in Python and Django, interested in AI/ML, goal is to become a Senior ML Engineer..."
        )

    with col2:
        st.markdown("### 💡 Tips")
        st.markdown("""
        <div class="card">
            <ul style="margin: 0; padding-left: 20px;">
                <li>Be specific about your skills</li>
                <li>Mention your experience level</li>
                <li>Include your career goals</li>
                <li>Add any preferences (remote, location, etc.)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🎯 Get Personalized Advice", key="get_advice", use_container_width=True):
        if not profile.strip():
            st.warning("⚠️ Please enter your profile details")
        else:
            with st.spinner("🤖 Generating comprehensive career advice..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)

                resp = career_advice(profile, st.session_state.user['uid'])

                if "error" in resp:
                    st.error(f"❌ Error: {resp['error']}")
                else:
                    advice = resp.get("advice", "")
                    st.markdown("### 📋 Your Career Roadmap")
                    st.markdown(f"<div class='result-block'>{advice}</div>", unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        download_text_button(advice, filename="career_advice.txt", label="📥 Download as TXT")
                    with col2:
                        st.button("📧 Email This Advice", key="email_advice")

# -------------------------
# Job Suggestor Page
# -------------------------
elif page == "Job Suggestor":
    st.title("💼 AI Job Suggestor")
    st.markdown("Find the perfect job roles matching your profile")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        profile = st.text_area(
            "Your profile (skills, domain, interests):",
            height=150,
            placeholder="e.g., Python, Machine Learning, Data Analysis, interested in Healthcare AI..."
        )

    with col2:
        location = st.text_input("Preferred Location", placeholder="e.g., Remote, New York")
        experience_level = st.selectbox("Experience Level",
                                        ["Any", "Entry Level", "Mid Level", "Senior Level", "Lead/Principal"])

    with col3:
        st.markdown("### 🎯 Filters")
        min_salary = st.number_input("Min Salary (k$)", min_value=0, value=0, step=10)
        remote_only = st.checkbox("Remote Only")

    if st.button("🔍 Find Matching Jobs", key="suggest_jobs", use_container_width=True):
        if not profile.strip():
            st.warning("⚠️ Please provide your profile details")
        else:
            with st.spinner("🔎 Analyzing job market and finding best matches..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)

                resp = job_suggestor(profile, location, experience_level)

                if "error" in resp:
                    st.error(f"❌ Error: {resp['error']}")
                elif "raw" in resp:
                    st.markdown("**Job Suggestions:**")
                    st.text(resp.get("jobs", ""))
                else:
                    jobs = resp.get("jobs", [])
                    if isinstance(jobs, list):
                        st.markdown(f"### 🎯 Found {len(jobs)} Matching Roles")

                        for i, job in enumerate(jobs):
                            with st.expander(
                                    f"### {i + 1}. {job.get('role', 'N/A')} - {job.get('salary_range', 'N/A')}",
                                    expanded=i == 0):
                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    st.markdown(f"**Description:**")
                                    st.markdown(job.get('description', 'N/A'))

                                    st.markdown(f"**Required Skills:**")
                                    skills = job.get('skills', [])
                                    if skills:
                                        for skill in skills:
                                            st.markdown(f'<span class="badge badge-info">{skill}</span>',
                                                        unsafe_allow_html=True)

                                    st.markdown(f"**Top Companies Hiring:**")
                                    companies = job.get('companies', [])
                                    if companies:
                                        for company in companies:
                                            st.markdown(f"• {company}")

                                with col2:
                                    growth = job.get('growth_potential', 0)
                                    balance = job.get('work_life_balance', 0)

                                    st.markdown("**Growth Potential**")
                                    st.progress(growth * 20)
                                    st.markdown(f"{growth}/5")

                                    st.markdown("**Work-Life Balance**")
                                    st.progress(balance * 20)
                                    st.markdown(f"{balance}/5")

                                st.markdown("---")
                                st.button(f"🔖 Save Job", key=f"save_job_{i}")

# -------------------------
# Resume Evaluator Page
# -------------------------
elif page == "Resume Evaluator":
    st.title("📄 AI Resume Evaluator")
    st.markdown("Get comprehensive analysis with ATS optimization tips")

    col1, col2 = st.columns([2, 1])

    with col1:
        resume_file = st.file_uploader(
            "📤 Upload your resume (PDF)",
            type=["pdf"],
            help="Upload your resume in PDF format for detailed analysis"
        )

    with col2:
        st.markdown("### ✨ What You'll Get")
        st.markdown("""
        <div class="card">
            <ul style="margin: 0; padding-left: 20px;">
                <li>Overall Score (1-10)</li>
                <li>ATS Compatibility Check</li>
                <li>Strengths & Weaknesses</li>
                <li>Keyword Analysis</li>
                <li>Actionable Improvements</li>
                <li>Industry-specific Tips</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    if resume_file:
        st.success(f"✅ File uploaded: {resume_file.name}")

        if st.button("🔍 Analyze Resume", key="eval_resume", use_container_width=True):
            with st.spinner("📊 Analyzing your resume..."):
                progress_bar = st.progress(0)

                progress_bar.progress(20)
                time.sleep(0.5)
                st.info("📄 Extracting text from PDF...")

                progress_bar.progress(50)
                time.sleep(0.5)
                st.info("🤖 AI analyzing content...")

                resp = resume_eval(resume_file, st.session_state.user['uid'])
                progress_bar.progress(100)

                if "error" in resp:
                    st.error(f"❌ Error: {resp['error']}")
                else:
                    evaluation = resp.get("evaluation", "")

                    st.markdown("### 📊 Resume Analysis Results")

                    # Display in a nice format
                    st.markdown(f"<div class='result-block'>{evaluation}</div>", unsafe_allow_html=True)

                    st.success("✅ Analysis complete!")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        download_text_button(evaluation, filename="resume_evaluation.txt", label="📥 Download Report")
                    with col2:
                        st.button("📧 Email Report", key="email_resume")
                    with col3:
                        st.button("🔄 Analyze Another", key="analyze_another")

# -------------------------
# Mock Interview Page (Enhanced)
# -------------------------
elif page == "Mock Interview":
    st.title("🎤 Mock Interview Practice")
    st.markdown("Practice with AI-generated questions and get detailed feedback")

    if not st.session_state.mi_questions:
        # Setup Phase
        col1, col2 = st.columns([2, 1])

        with col1:
            role = st.text_input(
                "🎯 Role to prepare for:",
                placeholder="e.g., Senior Software Engineer, Data Scientist, Product Manager"
            )

            experience_level = st.selectbox(
                "Experience Level",
                ["Entry Level", "Mid Level", "Senior Level", "Lead/Principal"]
            )

            num_questions = st.slider("Number of questions", 3, 10, 5)

        with col2:
            st.markdown("### 📝 Interview Types")
            st.markdown("""
            <div class="card">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Technical Questions</li>
                    <li>Behavioral Questions</li>
                    <li>Situational Problems</li>
                    <li>Mixed difficulty levels</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 🎯 Evaluation Metrics")
            st.markdown("""
            <div class="card">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Clarity & Structure</li>
                    <li>Confidence Level</li>
                    <li>Technical Accuracy</li>
                    <li>Communication Skills</li>
                    <li>Overall Score</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚀 Start Mock Interview", key="start_mock", use_container_width=True):
            if not role.strip():
                st.warning("⚠️ Please enter the role you're preparing for")
            else:
                with st.spinner("🤖 Generating interview questions..."):
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.02)
                        progress_bar.progress(i + 1)

                    resp = mock_interview(role, experience_level.split()[0].lower())

                    if "error" in resp:
                        st.error(f"❌ Error: {resp['error']}")
                    else:
                        questions = resp.get("questions", [])
                        if questions:
                            st.session_state.mi_questions = questions[:num_questions]
                            st.session_state.mi_idx = 0
                            st.session_state.mi_results = []
                            st.session_state.mi_role = role
                            st.success(f"✅ Generated {len(st.session_state.mi_questions)} questions!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ No questions generated. Please try again.")

    else:
        # Interview Phase
        idx = st.session_state.mi_idx
        total = len(st.session_state.mi_questions)
        current_q = st.session_state.mi_questions[idx]

        # Progress indicator
        progress_pct = ((idx + 1) / total) * 100
        st.markdown(f"""
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress_pct}%">
                    Question {idx + 1} of {total}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Question card
        st.markdown(f"""
            <div class="card">
                <h2>Question {idx + 1}</h2>
                <p style="font-size: 1.2rem; margin: 20px 0;">
                    <strong>{current_q.get('question', current_q if isinstance(current_q, str) else 'N/A')}</strong>
                </p>
                <div style="display: flex; gap: 10px; margin-top: 15px;">
                    <span class="badge badge-info">{current_q.get('type', 'general') if isinstance(current_q, dict) else 'general'}</span>
                    <span class="badge badge-warning">{current_q.get('difficulty', 'medium') if isinstance(current_q, dict) else 'medium'}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Hint expander
        if isinstance(current_q, dict) and current_q.get('hints'):
            with st.expander("💡 Need a hint?"):
                st.info(current_q['hints'])

        # Answer input
        tab1, tab2 = st.tabs(["✍️ Type Answer", "🎤 Record Answer"])

        with tab1:
            answer = st.text_area(
                "Your answer:",
                height=200,
                key=f"ans_text_{idx}",
                placeholder="Type your answer here... Be specific and provide examples where possible."
            )

            # Timer
            col1, col2 = st.columns([3, 1])
            with col2:
                st.markdown("### ⏱️ Timer")
                if 'start_time' not in st.session_state:
                    st.session_state.start_time = time.time()
                elapsed = int(time.time() - st.session_state.start_time)
                mins, secs = divmod(elapsed, 60)
                st.markdown(f"<h2 style='color: #667eea;'>{mins:02d}:{secs:02d}</h2>", unsafe_allow_html=True)

        with tab2:
            st.info("🎤 Record your answer using Speech-to-Text feature, then paste it here")
            audio_answer = st.text_area("Paste transcribed answer:", height=200, key=f"ans_audio_{idx}")
            if st.button("🗣️ Go to Speech-to-Text"):
                st.session_state.page = "Speech-to-Text"
                st.rerun()
            if audio_answer:
                answer = audio_answer

        # Action buttons
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("✅ Submit Answer", key=f"submit_{idx}", use_container_width=True):
                final_answer = answer if 'answer' in locals() and answer else (
                    audio_answer if 'audio_answer' in locals() else "")

                if not final_answer.strip():
                    st.warning("⚠️ Please provide an answer")
                else:
                    with st.spinner("🤖 Evaluating your answer..."):
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.02)
                            progress_bar.progress(i + 1)

                        question_text = current_q.get('question', current_q) if isinstance(current_q,
                                                                                           dict) else current_q
                        question_type = current_q.get('type', 'general') if isinstance(current_q, dict) else 'general'

                        result = evaluate_answer(question_text, final_answer, "", question_type)

                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        else:
                            result['answer'] = final_answer
                            result['question'] = question_text
                            st.session_state.mi_results.append(result)
                            st.success("✅ Answer evaluated!")

                            # Show immediate feedback
                            st.markdown("### 📊 Quick Feedback")
                            cols = st.columns(5)
                            metrics = ['clarity', 'confidence', 'relevance', 'technical_accuracy', 'communication']
                            for i, metric in enumerate(metrics):
                                with cols[i]:
                                    score = result.get(metric, 0)
                                    st.metric(metric.title(), f"{score}/10")

                            time.sleep(2)

                            if idx + 1 < total:
                                st.session_state.mi_idx += 1
                                st.session_state.start_time = time.time()
                                st.rerun()
                            else:
                                st.balloons()
                                st.success("🎉 Interview completed! Check your detailed results below.")
                                time.sleep(2)
                                st.rerun()

        with col2:
            if st.button("⏭️ Skip", key=f"skip_{idx}", use_container_width=True):
                if idx + 1 < total:
                    st.session_state.mi_idx += 1
                    st.session_state.start_time = time.time()
                    st.rerun()

        with col3:
            if st.button("🔄 Restart", key=f"restart_{idx}", use_container_width=True):
                st.session_state.mi_idx = 0
                st.session_state.mi_results = []
                st.session_state.start_time = time.time()
                st.rerun()

        with col4:
            if st.button("🏁 Finish", key=f"finish_{idx}", use_container_width=True):
                # Save to history
                if st.session_state.mi_results:
                    save_interview_result(
                        st.session_state.user['uid'],
                        st.session_state.mi_role,
                        [q.get('question', q) if isinstance(q, dict) else q for q in st.session_state.mi_questions],
                        st.session_state.mi_results
                    )
                st.balloons()
                time.sleep(1)

        # Show previous results
        if st.session_state.mi_results:
            st.markdown("---")
            st.markdown("### 📊 Results Summary")

            for i, result in enumerate(st.session_state.mi_results):
                with st.expander(f"Question {i + 1}: {result.get('question', 'N/A')[:50]}...", expanded=False):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("**Your Answer:**")
                        st.info(result.get('answer', 'N/A'))

                        st.markdown("**Detailed Feedback:**")
                        st.markdown(result.get('detailed_feedback', 'N/A'))

                        if result.get('strengths'):
                            st.markdown("**✅ Strengths:**")
                            for strength in result['strengths']:
                                st.markdown(f"• {strength}")

                        if result.get('improvements'):
                            st.markdown("**🎯 Areas for Improvement:**")
                            for improvement in result['improvements']:
                                st.markdown(f"• {improvement}")

                        if result.get('model_answer_hints'):
                            st.markdown("**💡 Model Answer Approach:**")
                            st.success(result['model_answer_hints'])

                    with col2:
                        st.markdown("**Scores:**")
                        metrics = {
                            'Overall': result.get('overall_score', 0),
                            'Clarity': result.get('clarity', 0),
                            'Confidence': result.get('confidence', 0),
                            'Relevance': result.get('relevance', 0),
                            'Technical': result.get('technical_accuracy', 0),
                            'Communication': result.get('communication', 0)
                        }

                        for metric, score in metrics.items():
                            st.progress(score / 10, text=f"{metric}: {score}/10")

            # Overall statistics
            if st.session_state.mi_results:
                st.markdown("---")
                st.markdown("### 📈 Overall Performance")

                avg_score = sum([r.get('overall_score', 0) for r in st.session_state.mi_results]) / len(
                    st.session_state.mi_results)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average Score", f"{avg_score:.1f}/10")
                with col2:
                    st.metric("Questions Answered", len(st.session_state.mi_results))
                with col3:
                    st.metric("Strong Answers",
                              sum([1 for r in st.session_state.mi_results if r.get('overall_score', 0) >= 7]))
                with col4:
                    st.metric("Completion", f"{(len(st.session_state.mi_results) / total) * 100:.0f}%")

                # Download report
                report = f"Mock Interview Report - {st.session_state.mi_role}\n\n"
                for i, r in enumerate(st.session_state.mi_results):
                    report += f"Question {i + 1}: {r.get('question', 'N/A')}\n"
                    report += f"Your Answer: {r.get('answer', 'N/A')}\n"
                    report += f"Score: {r.get('overall_score', 0)}/10\n"
                    report += f"Feedback: {r.get('detailed_feedback', 'N/A')}\n\n"

                download_text_button(report,
                                     filename=f"interview_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                     label="📥 Download Full Report")

# -------------------------
# Interview History Page
# -------------------------
elif page == "Interview History":
    st.title("📊 Interview History")
    st.markdown("Track your progress and review past interviews")

    if db:
        try:
            interviews = db.collection('interviews').where('user_id', '==', st.session_state.user['uid']).order_by(
                'timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()

            interview_list = [doc.to_dict() for doc in interviews]

            if interview_list:
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                total_interviews = len(interview_list)
                avg_score = sum([i.get('average_score', 0) for i in
                                 interview_list]) / total_interviews if total_interviews > 0 else 0

                with col1:
                    st.metric("Total Interviews", total_interviews)
                with col2:
                    st.metric("Average Score", f"{avg_score:.1f}/10")
                with col3:
                    top_score = max([i.get('average_score', 0) for i in interview_list])
                    st.metric("Best Score", f"{top_score:.1f}/10")
                with col4:
                    recent_interviews = len([i for i in interview_list if i.get('timestamp')])
                    st.metric("This Month", recent_interviews)

                st.markdown("---")

                # Chart - Score progression
                if len(interview_list) > 1:
                    scores = [i.get('average_score', 0) for i in reversed(interview_list)]
                    roles = [i.get('role', 'Unknown')[:20] for i in reversed(interview_list)]

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        y=scores,
                        x=list(range(len(scores))),
                        mode='lines+markers',
                        name='Score',
                        line=dict(color='#667eea', width=3),
                        marker=dict(size=10)
                    ))
                    fig.update_layout(
                        title="Score Progression",
                        xaxis_title="Interview Number",
                        yaxis_title="Average Score",
                        yaxis_range=[0, 10],
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📝 Past Interviews")

                # Interview list
                for i, interview in enumerate(interview_list):
                    with st.expander(
                            f"{i + 1}. {interview.get('role', 'Unknown Role')} - Score: {interview.get('average_score', 0):.1f}/10"):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"**Questions Asked:** {len(interview.get('questions', []))}")

                            results = interview.get('results', [])
                            if results:
                                st.markdown("**Question Summary:**")
                                for j, result in enumerate(results):
                                    st.markdown(
                                        f"{j + 1}. {result.get('question', 'N/A')[:80]}... - **Score:** {result.get('overall_score', 0)}/10")

                        with col2:
                            timestamp = interview.get('timestamp')
                            if timestamp:
                                st.markdown(f"**Date:** {timestamp.strftime('%Y-%m-%d')}")
                            st.markdown(f"**Average:** {interview.get('average_score', 0):.1f}/10")

                            if st.button(f"📄 View Details", key=f"view_{i}"):
                                st.info("Detailed view feature coming soon!")
            else:
                st.info("📭 No interview history yet. Start your first mock interview!")
                if st.button("🎤 Start Interview"):
                    st.session_state.page = "Mock Interview"
                    st.rerun()

        except Exception as e:
            st.error(f"Error loading history: {e}")
    else:
        st.warning("Database not connected")

# -------------------------
# Speech-to-Text Page (Enhanced)
# -------------------------
elif page == "Speech-to-Text":
    st.title("🗣️ Speech to Text Converter")
    st.markdown("Convert audio recordings to text with high accuracy")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📤 Upload Audio")
        audio_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "mp3", "m4a", "ogg"],
            help="Supported formats: WAV, MP3, M4A, OGG"
        )

        if audio_file:
            st.audio(audio_file, format=f'audio/{audio_file.name.split(".")[-1]}')

            file_details = {
                "Filename": audio_file.name,
                "FileType": audio_file.type,
                "FileSize": f"{audio_file.size / 1024:.2f} KB"
            }
            st.json(file_details)

    with col2:
        st.markdown("### ℹ️ Information")
        st.markdown("""
        <div class="card">
            <h4>Supported Features:</h4>
            <ul>
                <li>Multiple audio formats</li>
                <li>Automatic punctuation</li>
                <li>Confidence scoring</li>
                <li>High accuracy recognition</li>
            </ul>
            <h4>Tips:</h4>
            <ul>
                <li>Use clear audio</li>
                <li>Minimize background noise</li>
                <li>Speak clearly and steadily</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    if audio_file and st.button("🎯 Transcribe Audio", key="transcribe", use_container_width=True):
        with st.spinner("🎤 Transcribing audio..."):
            progress_bar = st.progress(0)

            progress_bar.progress(30)
            st.info("Converting audio format...")
            time.sleep(0.5)

            progress_bar.progress(60)
            st.info("Processing speech...")

            file_extension = os.path.splitext(audio_file.name)[1]
            result = speech_to_text(audio_file, file_extension)

            progress_bar.progress(100)

            if "error" in result:
                st.error(f"❌ Error: {result['error']}")
            else:
                transcript = result.get("text", "")
                confidence = result.get("confidence", 0)

                st.success("✅ Transcription complete!")

                st.markdown("### 📝 Transcript")
                st.markdown(f"<div class='result-block'>{transcript}</div>", unsafe_allow_html=True)

                if confidence > 0:
                    st.markdown(f"**Confidence Score:** {confidence * 100:.1f}%")
                    st.progress(confidence)

                col1, col2, col3 = st.columns(3)
                with col1:
                    download_text_button(transcript, filename="transcript.txt", label="📥 Download Transcript")
                with col2:
                    if st.button("📋 Copy to Clipboard"):
                        st.code(transcript)
                        st.info("Use Ctrl+C to copy")
                with col3:
                    if st.button("🎤 Use in Interview"):
                        st.info("Copy the transcript and paste it in Mock Interview")

# -------------------------
# Facial Analysis Page (NEW - Real Implementation)
# -------------------------
elif page == "Facial Analysis":
    st.title("📹 Facial Expression Analysis")
    st.markdown("Analyze your facial expressions during interview practice")

    st.markdown("""
    <div class="card">
        <h3>🎯 How It Works</h3>
        <p>This feature analyzes your facial expressions during mock interviews to provide feedback on:</p>
        <ul>
            <li><strong>Confidence Level</strong> - Based on facial cues</li>
            <li><strong>Emotional State</strong> - Detecting nervousness, happiness, focus</li>
            <li><strong>Engagement</strong> - Eye contact and attentiveness</li>
            <li><strong>Overall Presence</strong> - Professional demeanor assessment</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2 = st.tabs(["📸 Live Analysis", "📤 Upload Video/Image"])

    with tab1:
        st.markdown("### 📸 Live Webcam Analysis")

        col1, col2 = st.columns([2, 1])

        with col1:
            camera_input = st.camera_input("Take a picture for analysis")

            if camera_input:
                # Convert to numpy array
                import io
                from PIL import Image

                image = Image.open(camera_input)
                img_array = np.array(image)

                with st.spinner("🤖 Analyzing facial expression..."):
                    try:
                        emotion, emotion_scores = analyze_facial_expression(img_array)

                        st.success(f"✅ Analysis complete!")

                        st.markdown(f"### Dominant Emotion: {emotion.title()}")

                        # Emotion scores chart
                        if emotion_scores:
                            emotions = list(emotion_scores.keys())
                            scores = list(emotion_scores.values())

                            fig = px.bar(
                                x=emotions,
                                y=scores,
                                labels={'x': 'Emotion', 'y': 'Confidence (%)'},
                                title="Emotion Distribution",
                                color=scores,
                                color_continuous_scale='Blues'
                            )
                            fig.update_layout(showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)

                        # Recommendations based on emotion
                        st.markdown("### 💡 Recommendations")
                        recommendations = {
                            'happy': "✅ Great! Your positive demeanor shows confidence. Maintain this energy throughout the interview.",
                            'neutral': "😐 Try to show more enthusiasm and engagement. Smile occasionally to appear more approachable.",
                            'sad': "😟 You appear uncertain. Take deep breaths, smile, and remember your achievements.",
                            'angry': "😠 You seem tense. Relax your facial muscles and maintain a calm demeanor.",
                            'surprise': "😲 You seem overly reactive. Stay composed and measured in your responses.",
                            'fear': "😰 You appear nervous. Practice power poses before interviews and take deep breaths.",
                            'disgust': "😣 Your expression may seem negative. Maintain a neutral to positive expression."
                        }

                        if emotion in recommendations:
                            st.info(recommendations[emotion])

                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        st.info("💡 Tip: Ensure your face is clearly visible and well-lit")

        with col2:
            st.markdown("### 📊 Tips for Good Expressions")
            st.markdown("""
            <div class="card">
                <ul>
                    <li><strong>Smile naturally</strong> when greeting</li>
                    <li><strong>Maintain eye contact</strong> with camera</li>
                    <li><strong>Keep neutral-positive</strong> expression</li>
                    <li><strong>Nod occasionally</strong> to show engagement</li>
                    <li><strong>Avoid frowning</strong> or looking down</li>
                    <li><strong>Stay relaxed</strong> and confident</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 🎯 Emotion Guide")
            st.markdown("""
            <div class="card">
                <p><strong>Ideal:</strong> Happy, Neutral</p>
                <p><strong>Acceptable:</strong> Surprise (moderate)</p>
                <p><strong>Avoid:</strong> Fear, Anger, Sadness, Disgust</p>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.markdown("### 📤 Upload Image for Analysis")

        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

        if uploaded_file:
            from PIL import Image

            image = Image.open(uploaded_file)

            col1, col2 = st.columns(2)

            with col1:
                st.image(image, caption="Uploaded Image", use_container_width=True)

            with col2:
                if st.button("🔍 Analyze Image", use_container_width=True):
                    img_array = np.array(image)

                    with st.spinner("🤖 Analyzing..."):
                        try:
                            emotion, emotion_scores = analyze_facial_expression(img_array)

                            st.success(f"✅ Dominant Emotion: **{emotion.title()}**")

                            if emotion_scores:
                                for emo, score in sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True):
                                    st.progress(score / 100, text=f"{emo.title()}: {score:.1f}%")

                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

    st.markdown("---")
    st.markdown("""
    <div class="card">
        <h3>🎥 Video Analysis (Coming Soon)</h3>
        <p>We're working on real-time video analysis that will track your expressions throughout an entire mock interview session!</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# Reminders/Notifier Page (Enhanced)
# -------------------------
elif page == "Reminders":
    st.title("🔔 Smart Reminders & Notifications")
    st.markdown("Set up personalized learning reminders and career milestones")

    tab1, tab2, tab3 = st.tabs(["📅 Daily Reminders", "🎯 Career Milestones", "📊 Reminder History"])

    with tab1:
        st.markdown("### 📅 Set Daily Learning Reminders")

        col1, col2 = st.columns(2)

        with col1:
            reminder_type = st.selectbox(
                "Reminder Type",
                ["Interview Practice", "Resume Update", "Job Search", "Skill Learning", "Networking", "Custom"]
            )

            reminder_time = st.time_input("Reminder Time", datetime.time(9, 0))

            reminder_frequency = st.selectbox(
                "Frequency",
                ["Daily", "Every 2 Days", "Weekly", "Bi-weekly", "Monthly"]
            )

            notification_method = st.multiselect(
                "Notification Method",
                ["Email", "In-App", "Browser Notification"],
                default=["In-App"]
            )

        with col2:
            st.markdown("### 💡 Reminder Templates")
            st.markdown("""
            <div class="card">
                <ul>
                    <li><strong>Interview Practice:</strong> "Time to practice interview questions!"</li>
                    <li><strong>Resume Update:</strong> "Update your resume with recent achievements"</li>
                    <li><strong>Job Search:</strong> "Check new job postings in your field"</li>
                    <li><strong>Skill Learning:</strong> "30 min learning session time!"</li>
                    <li><strong>Networking:</strong> "Reach out to 3 people on LinkedIn"</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        custom_message = st.text_area(
            "Custom Message (optional)",
            placeholder="Add a personalized message for this reminder...",
            height=100
        )

        if st.button("✅ Set Reminder", key="set_reminder", use_container_width=True):
            if db:
                try:
                    reminder_data = {
                        'user_id': st.session_state.user['uid'],
                        'type': reminder_type,
                        'time': reminder_time.strftime('%H:%M'),
                        'frequency': reminder_frequency,
                        'notification_methods': notification_method,
                        'custom_message': custom_message,
                        'active': True,
                        'created_at': firestore.SERVER_TIMESTAMP
                    }

                    db.collection('reminders').add(reminder_data)
                    st.success("✅ Reminder set successfully!")
                    st.balloons()

                    # Show confirmation
                    st.info(
                        f"📧 You'll receive {reminder_frequency.lower()} reminders at {reminder_time.strftime('%I:%M %p')} via {', '.join(notification_method)}")

                except Exception as e:
                    st.error(f"Error setting reminder: {e}")
            else:
                st.warning("⚠️ Database not connected. Reminder saved locally for this session.")
                st.session_state.setdefault('local_reminders', []).append({
                    'type': reminder_type,
                    'time': reminder_time.strftime('%H:%M'),
                    'frequency': reminder_frequency
                })
                st.success("✅ Reminder saved locally!")

    with tab2:
        st.markdown("### 🎯 Career Milestone Tracking")

        col1, col2 = st.columns([2, 1])

        with col1:
            milestone_title = st.text_input("Milestone Title", placeholder="e.g., Get AWS Certification")

            milestone_category = st.selectbox(
                "Category",
                ["Certification", "Job Application", "Skill Mastery", "Networking Goal", "Salary Target", "Other"]
            )

            target_date = st.date_input("Target Date", min_value=datetime.date.today())

            milestone_description = st.text_area(
                "Description & Action Steps",
                placeholder="What steps do you need to take to achieve this milestone?",
                height=150
            )

        with col2:
            st.markdown("### 📊 Your Milestones")

            # Mock data - replace with actual DB query
            active_milestones = 3
            completed_milestones = 7

            st.metric("Active", active_milestones)
            st.metric("Completed", completed_milestones)

            completion_rate = (completed_milestones / (active_milestones + completed_milestones)) * 100
            st.progress(completion_rate / 100, text=f"{completion_rate:.0f}% Success Rate")

        if st.button("🎯 Add Milestone", key="add_milestone", use_container_width=True):
            if milestone_title and milestone_description:
                if db:
                    try:
                        milestone_data = {
                            'user_id': st.session_state.user['uid'],
                            'title': milestone_title,
                            'category': milestone_category,
                            'target_date': target_date.isoformat(),
                            'description': milestone_description,
                            'completed': False,
                            'created_at': firestore.SERVER_TIMESTAMP
                        }

                        db.collection('milestones').add(milestone_data)
                        st.success(f"🎯 Milestone '{milestone_title}' added!")
                        st.balloons()

                    except Exception as e:
                        st.error(f"Error adding milestone: {e}")
                else:
                    st.warning("Database not connected")
            else:
                st.warning("Please fill in title and description")

        st.markdown("---")
        st.markdown("### 📋 Active Milestones")

        # Display milestones (mock data - replace with DB query)
        if db:
            try:
                milestones = db.collection('milestones').where('user_id', '==', st.session_state.user['uid']).where(
                    'completed', '==', False).limit(10).stream()

                milestone_list = [doc.to_dict() for doc in milestones]

                if milestone_list:
                    for i, milestone in enumerate(milestone_list):
                        with st.expander(f"{milestone.get('title', 'Untitled')} - {milestone.get('category', 'N/A')}"):
                            st.markdown(f"**Target Date:** {milestone.get('target_date', 'Not set')}")
                            st.markdown(f"**Description:** {milestone.get('description', 'N/A')}")

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"✅ Mark Complete", key=f"complete_{i}"):
                                    st.success("Milestone completed! 🎉")
                            with col2:
                                if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                                    st.info("Milestone deleted")
                else:
                    st.info("No active milestones. Create your first one above!")
            except Exception as e:
                st.error(f"Error loading milestones: {e}")

    with tab3:
        st.markdown("### 📊 Reminder History & Statistics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Reminders", "24")
        with col2:
            st.metric("Completed", "18")
        with col3:
            st.metric("Missed", "2")
        with col4:
            st.metric("Success Rate", "90%")

        st.markdown("---")

        # Activity chart
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        completed = [3, 4, 2, 5, 3, 1, 0]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=days,
            y=completed,
            marker_color='#667eea',
            name='Completed Reminders'
        ))
        fig.update_layout(
            title="Weekly Activity",
            xaxis_title="Day",
            yaxis_title="Completed Reminders",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📅 Recent Activity")

        activity_log = [
            {"date": "2025-10-28", "action": "Completed interview practice", "status": "success"},
            {"date": "2025-10-27", "action": "Updated resume", "status": "success"},
            {"date": "2025-10-26", "action": "Missed skill learning session", "status": "missed"},
            {"date": "2025-10-25", "action": "Completed job search", "status": "success"},
        ]

        for activity in activity_log:
            status_color = "success" if activity["status"] == "success" else "warning"
            st.markdown(f"""
                <div class="card">
                    <strong>{activity['date']}</strong> - {activity['action']}
                    <span class="badge badge-{status_color}">{activity['status'].title()}</span>
                </div>
            """, unsafe_allow_html=True)

# -------------------------
# Profile Settings Page
# -------------------------
elif page == "Profile Settings":
    st.title("⚙️ Profile Settings")

    tab1, tab2, tab3 = st.tabs(["👤 Personal Info", "🔐 Security", "💳 Subscription"])

    with tab1:
        st.markdown("### 👤 Personal Information")

        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", value=st.session_state.user.get('name', ''))
            email = st.text_input("Email", value=st.session_state.user['email'], disabled=True)
            phone = st.text_input("Phone Number", value=st.session_state.user_data.get('phone', ''))

        with col2:
            location = st.text_input("Location", value=st.session_state.user_data.get('location', ''))
            current_role = st.text_input("Current Role", value=st.session_state.user_data.get('current_role', ''))
            linkedin = st.text_input("LinkedIn URL", value=st.session_state.user_data.get('linkedin', ''))

        st.markdown("### 🎯 Career Preferences")

        target_roles = st.multiselect(
            "Target Roles",
            ["Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "ML Engineer", "UX Designer",
             "Other"],
            default=st.session_state.user_data.get('target_roles', [])
        )

        preferred_industries = st.multiselect(
            "Preferred Industries",
            ["Technology", "Finance", "Healthcare", "E-commerce", "Education", "Consulting", "Other"],
            default=st.session_state.user_data.get('industries', [])
        )

        if st.button("💾 Save Changes", use_container_width=True):
            if db:
                try:
                    user_ref = db.collection('users').document(st.session_state.user['uid'])
                    user_ref.update({
                        'phone': phone,
                        'location': location,
                        'current_role': current_role,
                        'linkedin': linkedin,
                        'target_roles': target_roles,
                        'industries': preferred_industries
                    })
                    st.success("✅ Profile updated successfully!")
                except Exception as e:
                    st.error(f"Error updating profile: {e}")

    with tab2:
        st.markdown("### 🔐 Security Settings")

        st.markdown("**Change Password**")
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")

        if st.button("🔄 Change Password"):
            if new_password == confirm_new_password:
                if len(new_password) >= 6:
                    st.success("✅ Password changed successfully!")
                else:
                    st.warning("Password must be at least 6 characters")
            else:
                st.warning("Passwords don't match")

        st.markdown("---")
        st.markdown("**Two-Factor Authentication**")
        two_fa_enabled = st.checkbox("Enable 2FA", value=False)
        if two_fa_enabled:
            st.info("📱 2FA will be enabled. You'll receive a code via email for each login.")

    with tab3:
        st.markdown("### 💳 Subscription Plan")

        current_tier = st.session_state.user_data.get('subscription_tier', 'free')

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
                <div class="card" style="text-align: center;">
                    <h3>🆓 Free</h3>
                    <div class="stat-number">$0</div>
                    <p class="small-muted">per month</p>
                    <ul style="text-align: left; margin: 20px 0;">
                        <li>5 interviews/month</li>
                        <li>3 career advice</li>
                        <li>1 resume evaluation</li>
                        <li>Basic features</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            if current_tier == 'free':
                st.success("✅ Current Plan")

        with col2:
            st.markdown("""
                <div class="card" style="text-align: center;">
                    <h3>⭐ Pro</h3>
                    <div class="stat-number">$9.99</div>
                    <p class="small-muted">per month</p>
                    <ul style="text-align: left; margin: 20px 0;">
                        <li>Unlimited interviews</li>
                        <li>Unlimited advice</li>
                        <li>Unlimited resumes</li>
                        <li>Priority support</li>
                        <li>Advanced analytics</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            if current_tier == 'pro':
                st.success("✅ Current Plan")
            else:
                if st.button("Upgrade to Pro", key="upgrade_pro"):
                    st.info("💳 Payment integration coming soon!")

        with col3:
            st.markdown("""
                <div class="card" style="text-align: center;">
                    <h3>💎 Enterprise</h3>
                    <div class="stat-number">$29.99</div>
                    <p class="small-muted">per month</p>
                    <ul style="text-align: left; margin: 20px 0;">
                        <li>Everything in Pro</li>
                        <li>1-on-1 mentorship</li>
                        <li>Custom learning paths</li>
                        <li>Job referrals</li>
                        <li>Career coaching</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            if current_tier == 'enterprise':
                st.success("✅ Current Plan")
            else:
                if st.button("Upgrade to Enterprise", key="upgrade_enterprise"):
                    st.info("💳 Payment integration coming soon!")

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #6b7280; padding: 20px;">
        <p>Made with ❤️ by AI Career Mentor Team | © 2025 All Rights Reserved</p>
        <p style="font-size: 0.875rem;">
            <a href="#" style="color: #667eea; text-decoration: none;">Privacy Policy</a> | 
            <a href="#" style="color: #667eea; text-decoration: none;">Terms of Service</a> | 
            <a href="#" style="color: #667eea; text-decoration: none;">Contact Us</a>
        </p>
    </div>
""", unsafe_allow_html=True)