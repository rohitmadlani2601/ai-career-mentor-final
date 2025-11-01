from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import google.generativeai as genai
from google.cloud import speech
import PyPDF2
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from pydub import AudioSegment
import tempfile
#from deepface import DeepFace
import numpy as np
import cv2
import base64
import logging
from video_analyzer import VideoInterviewAnalyzer

# -------------------------
# Flask App Setup
# -------------------------
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# Environment Variables
# -------------------------
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "rohitmadlani2006@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "npdj tdgo pugd qrfr")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# -------------------------
# Firebase Initialization
# -------------------------
if not firebase_admin._apps:
    try:
        cred_path = os.environ.get("FIREBASE_CREDENTIALS", "E:\GenAI\ai_career_mentor\aicareermentor-1b611-firebase-adminsdk-fbsvc-e20fe87c4d.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        db = None
else:
    db = firestore.client()

# -------------------------
# Gemini Configuration
# -------------------------
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
    MODEL_NAME = "gemini-2.5-pro"
    logger.info("Gemini API configured")
else:
    logger.warning("GOOGLE_API_KEY not set")

# -------------------------
# Scheduler for Reminders
# -------------------------
scheduler = BackgroundScheduler()
scheduler.start()


# -------------------------
# Authentication Decorator
# -------------------------
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "No authorization token provided"}), 401

        try:
            # Verify Firebase token
            decoded_token = auth.verify_id_token(token.replace('Bearer ', ''))
            request.user_id = decoded_token['uid']
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    return decorated_function


# -------------------------
# Utility Functions
# -------------------------
def send_email(to_email, subject, body, html=False):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email

        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False


def update_user_stats(user_id, stat_type):
    """Update user statistics in Firestore"""
    if db and user_id:
        try:
            user_ref = db.collection('users').document(user_id)
            user_ref.update({stat_type: firestore.Increment(1)})
            logger.info(f"Updated {stat_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating stats: {e}")


def convert_audio_to_wav(audio_bytes, input_format="mp3"):
    """Convert audio to WAV format"""
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_format}") as temp_input:
            temp_input.write(audio_bytes)
            temp_input_path = temp_input.name

        # Convert to WAV
        audio = AudioSegment.from_file(temp_input_path, format=input_format)
        audio = audio.set_frame_rate(16000).set_channels(1)

        temp_output_path = temp_input_path.replace(f".{input_format}", ".wav")
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


# def analyze_facial_expression(image_data):
#     """Analyze facial expression from image data"""
#     try:
#         # Decode base64 image
#         img_bytes = base64.b64decode(image_data.split(',')[1])
#         nparr = np.frombuffer(img_bytes, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#
#         # Analyze the image
#         # DeepFace disabled due to TensorFlow errors
#         return {
#             'dominant_emotion': 'neutral',
#             'emotions': {}
#         }
#     except Exception as e:
#         raise Exception(f"Facial analysis failed: {e}")




def schedule_reminder(user_id, reminder_data):
    """Schedule a reminder using APScheduler"""
    try:
        reminder_time = datetime.datetime.strptime(reminder_data['time'], '%H:%M').time()
        frequency = reminder_data.get('frequency', 'daily')

        # Get user email
        if db:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_email = user_doc.to_dict().get('email')

                # Schedule based on frequency
                if frequency.lower() == 'daily':
                    scheduler.add_job(
                        send_reminder_email,
                        'cron',
                        hour=reminder_time.hour,
                        minute=reminder_time.minute,
                        args=[user_email, reminder_data]
                    )
                elif frequency.lower() == 'weekly':
                    scheduler.add_job(
                        send_reminder_email,
                        'cron',
                        day_of_week='mon',
                        hour=reminder_time.hour,
                        minute=reminder_time.minute,
                        args=[user_email, reminder_data]
                    )

                logger.info(f"Reminder scheduled for user {user_id}")
                return True
    except Exception as e:
        logger.error(f"Error scheduling reminder: {e}")
        return False


def send_reminder_email(email, reminder_data):
    """Send reminder email"""
    subject = f"🔔 Reminder: {reminder_data.get('type', 'Task')}"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #667eea;">Career Mentor Reminder</h2>
        <p>Hi there! 👋</p>
        <p>This is your scheduled reminder:</p>
        <div style="background: #f0f4ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #667eea; margin-top: 0;">{reminder_data.get('type', 'Task')}</h3>
            <p>{reminder_data.get('custom_message', 'Time to work on your career goals!')}</p>
        </div>
        <p>Keep up the great work! 💪</p>
        <p style="color: #6b7280; font-size: 0.875rem;">
            Best regards,<br>
            AI Career Mentor Team
        </p>
    </body>
    </html>
    """

    send_email(email, subject, body, html=True)


# -------------------------
# API Routes
# -------------------------

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "gemini_configured": bool(GENAI_API_KEY),
        "firebase_connected": db is not None
    })


# -------------------------
# Authentication Routes
# -------------------------

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Create new user account"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        # Create user in Firebase Auth
        user = auth.create_user(email=email, password=password)

        # Create user profile in Firestore
        if db:
            db.collection('users').document(user.uid).set({
                'email': email,
                'created_at': firestore.SERVER_TIMESTAMP,
                'total_interviews': 0,
                'total_advice_requests': 0,
                'total_resume_evals': 0,
                'subscription_tier': 'free'
            })

        return jsonify({
            "success": True,
            "user_id": user.uid,
            "message": "Account created successfully"
        }), 201

    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({"error": str(e)}), 400


@app.route('/api/auth/signin', methods=['POST'])
def signin():
    """Sign in user"""
    try:
        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({"error": "Email required"}), 400

        user = auth.get_user_by_email(email)

        return jsonify({
            "success": True,
            "user_id": user.uid,
            "email": user.email
        })

    except Exception as e:
        logger.error(f"Signin error: {e}")
        return jsonify({"error": str(e)}), 400


# -------------------------
# Career Advice Routes
# -------------------------

@app.route('/api/career-advice', methods=['POST'])
@require_auth
def career_advice():
    """Generate career advice"""
    try:
        data = request.json
        profile = data.get('profile', '')

        if not profile:
            return jsonify({"error": "Profile required"}), 400

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

        # Update user stats
        update_user_stats(request.user_id, 'total_advice_requests')

        return jsonify({
            "advice": response.text
        })

    except Exception as e:
        logger.error(f"Career advice error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Job Suggestor Routes
# -------------------------

@app.route('/api/job-suggestor', methods=['POST'])
@require_auth
def job_suggestor():
    """Suggest jobs based on profile"""
    try:
        data = request.json
        profile = data.get('profile', '')
        location = data.get('location', '')
        experience_level = data.get('experience_level', '')

        if not profile:
            return jsonify({"error": "Profile required"}), 400

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

        # Clean and parse JSON
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*', '', text).strip()

        try:
            jobs = json.loads(text)
            return jsonify({"jobs": jobs})
        except:
            return jsonify({"jobs": text, "raw": True})

    except Exception as e:
        logger.error(f"Job suggestor error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Resume Evaluator Routes
# -------------------------

@app.route('/api/resume-eval', methods=['POST'])
@require_auth
def resume_eval():
    """Evaluate resume"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']

        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files supported"}), 400

        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return jsonify({"error": "Could not extract text from PDF"}), 400

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

        # Update user stats
        update_user_stats(request.user_id, 'total_resume_evals')

        return jsonify({
            "evaluation": response.text
        })

    except Exception as e:
        logger.error(f"Resume eval error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Mock Interview Routes
# -------------------------

@app.route('/api/mock-interview/generate', methods=['POST'])
@require_auth
def generate_interview_questions():
    """Generate interview questions"""
    try:
        data = request.json
        role = data.get('role', '')
        experience_level = data.get('experience_level', 'mid')
        num_questions = data.get('num_questions', 5)

        if not role:
            return jsonify({"error": "Role required"}), 400

        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""Generate {num_questions} realistic interview questions for: {role}
Experience Level: {experience_level}

Include:
- Technical questions
- Behavioral questions
- Situational/problem-solving questions

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

        # Clean and parse JSON
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*', '', text).strip()

        try:
            questions = json.loads(text)
            return jsonify({"questions": questions})
        except:
            # Fallback
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            questions = [{"question": q, "type": "general", "difficulty": "medium", "hints": ""}
                         for q in lines[:num_questions]]
            return jsonify({"questions": questions})

    except Exception as e:
        logger.error(f"Generate questions error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/mock-interview/evaluate', methods=['POST'])
@require_auth
def evaluate_answer():
    """Evaluate interview answer"""
    try:
        data = request.json
        question = data.get('question', '')
        answer = data.get('answer', '')
        question_type = data.get('question_type', 'general')

        if not question or not answer:
            return jsonify({"error": "Question and answer required"}), 400

        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""You are an expert HR interviewer evaluating a candidate.

Question Type: {question_type}
Question: {question}
Candidate's Answer: {answer}

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

        # Clean and parse JSON
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*', '', text).strip()

        try:
            evaluation = json.loads(text)
            return jsonify(evaluation)
        except:
            return jsonify({
                "clarity": 5, "confidence": 5, "relevance": 5,
                "technical_accuracy": 5, "communication": 5, "overall_score": 5,
                "strengths": [], "improvements": [],
                "detailed_feedback": response.text,
                "model_answer_hints": ""
            })

    except Exception as e:
        logger.error(f"Evaluate answer error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/mock-interview/save', methods=['POST'])
@require_auth
def save_interview():
    """Save interview results"""
    try:
        data = request.json
        role = data.get('role', '')
        questions = data.get('questions', [])
        results = data.get('results', [])

        if db:
            avg_score = sum([r.get('overall_score', 0) for r in results]) / len(results) if results else 0

            db.collection('interviews').add({
                'user_id': request.user_id,
                'role': role,
                'questions': questions,
                'results': results,
                'average_score': avg_score,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            update_user_stats(request.user_id, 'total_interviews')

            return jsonify({
                "success": True,
                "message": "Interview saved successfully"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Save interview error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Speech-to-Text Routes
# -------------------------

@app.route('/api/speech-to-text', methods=['POST'])
@require_auth
def speech_to_text():
    """Convert speech to text"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        file_extension = os.path.splitext(file.filename)[1].lower()

        audio_content = file.read()

        # Convert to WAV if needed
        if file_extension in ['.mp3', '.m4a', '.ogg']:
            audio_content = convert_audio_to_wav(audio_content, file_extension[1:])

        # Use Google Speech-to-Text
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
            return jsonify({"text": "", "confidence": 0})

        transcript = " ".join([r.alternatives[0].transcript for r in response.results])
        confidence = sum([r.alternatives[0].confidence for r in response.results]) / len(response.results)

        return jsonify({
            "text": transcript,
            "confidence": confidence
        })

    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Facial Analysis Routes
# -------------------------

# @app.route('/api/facial-analysis', methods=['POST'])
# @require_auth
# def facial_analysis():
#     """Analyze facial expression"""
#     try:
#         data = request.json
#         image_data = data.get('image')
#
#         if not image_data:
#             return jsonify({"error": "Image data required"}), 400
#
#         result = analyze_facial_expression(image_data)
#
#         return jsonify(result)
#
#     except Exception as e:
#         logger.error(f"Facial analysis error: {e}")
#         return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-video', methods=['POST'])
def analyze_video():
    """Analyze uploaded interview video or image"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        filename = file.filename.lower()
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)

        analyzer = VideoInterviewAnalyzer()

        # Detect if the file is an image (jpg/png)
        if any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            import cv2
            frame = cv2.imread(temp_path)
            results = analyzer.analyze_single_frame(frame)
        else:
            results = analyzer.analyze_video(temp_path)

        os.remove(temp_path)
        return jsonify(results)

    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Reminder Routes
# -------------------------

@app.route('/api/reminders', methods=['POST'])
@require_auth
def create_reminder():
    """Create a new reminder"""
    try:
        data = request.json

        reminder_data = {
            'user_id': request.user_id,
            'type': data.get('type'),
            'time': data.get('time'),
            'frequency': data.get('frequency'),
            'notification_methods': data.get('notification_methods', []),
            'custom_message': data.get('custom_message', ''),
            'active': True,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        if db:
            doc_ref = db.collection('reminders').add(reminder_data)

            # Schedule the reminder
            schedule_reminder(request.user_id, reminder_data)

            return jsonify({
                "success": True,
                "reminder_id": doc_ref[1].id,
                "message": "Reminder created successfully"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Create reminder error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reminders', methods=['GET'])
@require_auth
def get_reminders():
    """Get user's reminders"""
    try:
        if db:
            reminders = db.collection('reminders').where('user_id', '==', request.user_id).where('active', '==',
                                                                                                 True).stream()

            reminder_list = []
            for doc in reminders:
                reminder = doc.to_dict()
                reminder['id'] = doc.id
                reminder_list.append(reminder)

            return jsonify({"reminders": reminder_list})
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Get reminders error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reminders/<reminder_id>', methods=['DELETE'])
@require_auth
def delete_reminder(reminder_id):
    """Delete a reminder"""
    try:
        if db:
            db.collection('reminders').document(reminder_id).update({'active': False})

            return jsonify({
                "success": True,
                "message": "Reminder deleted successfully"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Delete reminder error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Milestone Routes
# -------------------------

@app.route('/api/milestones', methods=['POST'])
@require_auth
def create_milestone():
    """Create a career milestone"""
    try:
        data = request.json

        milestone_data = {
            'user_id': request.user_id,
            'title': data.get('title'),
            'category': data.get('category'),
            'target_date': data.get('target_date'),
            'description': data.get('description'),
            'completed': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        if db:
            doc_ref = db.collection('milestones').add(milestone_data)

            return jsonify({
                "success": True,
                "milestone_id": doc_ref[1].id,
                "message": "Milestone created successfully"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Create milestone error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/milestones', methods=['GET'])
@require_auth
def get_milestones():
    """Get user's milestones"""
    try:
        if db:
            completed = request.args.get('completed', 'false').lower() == 'true'

            milestones = db.collection('milestones').where('user_id', '==', request.user_id).where('completed', '==',
                                                                                                   completed).stream()

            milestone_list = []
            for doc in milestones:
                milestone = doc.to_dict()
                milestone['id'] = doc.id
                milestone_list.append(milestone)

            return jsonify({"milestones": milestone_list})
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Get milestones error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/milestones/<milestone_id>/complete', methods=['PUT'])
@require_auth
def complete_milestone(milestone_id):
    """Mark milestone as complete"""
    try:
        if db:
            db.collection('milestones').document(milestone_id).update({
                'completed': True,
                'completed_at': firestore.SERVER_TIMESTAMP
            })

            return jsonify({
                "success": True,
                "message": "Milestone marked as complete"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Complete milestone error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# User Stats Routes
# -------------------------

@app.route('/api/user/stats', methods=['GET'])
@require_auth
def get_user_stats():
    """Get user statistics"""
    try:
        if db:
            user_doc = db.collection('users').document(request.user_id).get()

            if user_doc.exists:
                stats = user_doc.to_dict()
                return jsonify(stats)
            else:
                return jsonify({"error": "User not found"}), 404
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Get user stats error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """Update user profile"""
    try:
        data = request.json

        if db:
            user_ref = db.collection('users').document(request.user_id)
            user_ref.update(data)

            return jsonify({
                "success": True,
                "message": "Profile updated successfully"
            })
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Interview History Routes
# -------------------------

@app.route('/api/interviews/history', methods=['GET'])
@require_auth
def get_interview_history():
    """Get user's interview history"""
    try:
        if db:
            limit = int(request.args.get('limit', 20))

            interviews = db.collection('interviews').where('user_id', '==', request.user_id).order_by('timestamp',
                                                                                                      direction=firestore.Query.DESCENDING).limit(
                limit).stream()

            interview_list = []
            for doc in interviews:
                interview = doc.to_dict()
                interview['id'] = doc.id
                # Convert timestamp to string
                if 'timestamp' in interview and interview['timestamp']:
                    interview['timestamp'] = interview['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                interview_list.append(interview)

            return jsonify({"interviews": interview_list})
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Get interview history error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Email Notification Routes
# -------------------------

@app.route('/api/email/send', methods=['POST'])
@require_auth
def send_email_notification():
    """Send email notification"""
    try:
        data = request.json

        # Get user email
        if db:
            user_doc = db.collection('users').document(request.user_id).get()
            if user_doc.exists:
                user_email = user_doc.to_dict().get('email')

                subject = data.get('subject', 'Notification from AI Career Mentor')
                body = data.get('body', '')
                html = data.get('html', False)

                success = send_email(user_email, subject, body, html)

                if success:
                    return jsonify({
                        "success": True,
                        "message": "Email sent successfully"
                    })
                else:
                    return jsonify({"error": "Failed to send email"}), 500
            else:
                return jsonify({"error": "User not found"}), 404
        else:
            return jsonify({"error": "Database not connected"}), 500

    except Exception as e:
        logger.error(f"Send email error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------
# Error Handlers
# -------------------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# -------------------------
# Run Server
# -------------------------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)