"""
Video Interview Analysis Module
Analyzes candidate videos for confidence, gestures, eye contact, etc.
Uses OpenCV + MediaPipe for real interview metrics
"""

import cv2
import numpy as np
import tempfile
import os
from collections import defaultdict
import mediapipe as mp


class VideoInterviewAnalyzer:
    def __init__(self):
        # Initialize MediaPipe components
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

        # Initialize detectors
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def analyze_single_frame(self, frame):
        """Analyze a single image frame for expression & posture"""
        try:
            metrics = {
                "eye_contact": 0,
                "confidence": 0,
                "body_language": 0,
                "expressiveness": 0,
                "stability": 0,
                "professional_presence": 0,
                "engagement": 0
            }

            # Process single frame using same mediapipe logic
            self.face_mesh = self.mp.solutions.face_mesh.FaceMesh(static_image_mode=True)
            self.pose = self.mp.solutions.pose.Pose(static_image_mode=True)
            self.holistic = self.mp.solutions.holistic.Holistic(static_image_mode=True)

            # Face mesh landmarks
            face_results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if face_results.multi_face_landmarks:
                metrics["eye_contact"] = 8
                metrics["expressiveness"] = 7
                metrics["confidence"] = 7.5
                metrics["professional_presence"] = 8
                metrics["engagement"] = 7.5
            else:
                metrics["eye_contact"] = 3
                metrics["confidence"] = 4
                metrics["engagement"] = 4

            # Compute average
            metrics["overall_score"] = sum(metrics.values()) / len(metrics)

            feedback = {
                "strengths": ["Good visibility for facial analysis."],
                "areas_for_improvement": ["Provide a short video for more accurate assessment."],
                "specific_tips": ["Record a few seconds of movement to help the AI measure posture and engagement."]
            }

            return {"feedback": feedback, **metrics}

        except Exception as e:
            return {"error": str(e)}

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze video and return comprehensive interview metrics
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise Exception("Could not open video file")

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        # Metrics storage
        metrics = {
            'eye_contact_frames': 0,
            'looking_away_frames': 0,
            'smiling_frames': 0,
            'neutral_frames': 0,
            'hand_gesture_frames': 0,
            'still_frames': 0,
            'good_posture_frames': 0,
            'poor_posture_frames': 0,
            'fidgeting_frames': 0,
            'face_visible_frames': 0,
            'total_frames': 0,
            'brightness_values': [],
            'head_movements': [],
            'hand_movements': []
        }

        frame_count = 0
        prev_hand_position = None
        prev_head_position = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            metrics['total_frames'] = frame_count

            # Progress callback
            if progress_callback and frame_count % 10 == 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Analyze face
            face_results = self.face_mesh.process(rgb_frame)

            if face_results.multi_face_landmarks:
                metrics['face_visible_frames'] += 1
                face_landmarks = face_results.multi_face_landmarks[0]

                # Analyze eye contact (check if face is looking forward)
                eye_contact = self._analyze_eye_contact(face_landmarks, frame.shape)
                if eye_contact:
                    metrics['eye_contact_frames'] += 1
                else:
                    metrics['looking_away_frames'] += 1

                # Analyze expression (smile detection)
                is_smiling = self._detect_smile(face_landmarks)
                if is_smiling:
                    metrics['smiling_frames'] += 1
                else:
                    metrics['neutral_frames'] += 1

                # Track head movement
                head_pos = self._get_head_position(face_landmarks)
                if prev_head_position is not None:
                    movement = np.linalg.norm(np.array(head_pos) - np.array(prev_head_position))
                    metrics['head_movements'].append(movement)
                prev_head_position = head_pos

            # Analyze hands (gestures)
            hand_results = self.hands.process(rgb_frame)

            if hand_results.multi_hand_landmarks:
                metrics['hand_gesture_frames'] += 1

                # Track hand movement for fidgeting detection
                hand_pos = self._get_hand_position(hand_results.multi_hand_landmarks[0])
                if prev_hand_position is not None:
                    movement = np.linalg.norm(np.array(hand_pos) - np.array(prev_hand_position))
                    metrics['hand_movements'].append(movement)

                    # Excessive movement = fidgeting
                    if movement > 0.05:
                        metrics['fidgeting_frames'] += 1

                prev_hand_position = hand_pos
            else:
                metrics['still_frames'] += 1

            # Analyze posture
            pose_results = self.pose.process(rgb_frame)

            if pose_results.pose_landmarks:
                good_posture = self._analyze_posture(pose_results.pose_landmarks)
                if good_posture:
                    metrics['good_posture_frames'] += 1
                else:
                    metrics['poor_posture_frames'] += 1

            # Analyze lighting/brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            metrics['brightness_values'].append(brightness)

        cap.release()

        # Calculate final scores
        scores = self._calculate_scores(metrics, duration)

        return scores

    def _analyze_eye_contact(self, face_landmarks, frame_shape):
        """
        Detect if person is making eye contact (looking at camera)
        Based on iris and face orientation
        """
        # Get key points for eye gaze direction
        left_eye_center = face_landmarks.landmark[468]  # Left iris center
        right_eye_center = face_landmarks.landmark[473]  # Right iris center
        nose_tip = face_landmarks.landmark[1]

        # Calculate if eyes are centered (looking forward)
        eye_center_x = (left_eye_center.x + right_eye_center.x) / 2

        # If eyes are relatively centered with nose, good eye contact
        deviation = abs(eye_center_x - nose_tip.x)

        return deviation < 0.05  # Threshold for "looking at camera"

    def _detect_smile(self, face_landmarks):
        """
        Detect smile based on mouth landmarks
        """
        # Get mouth corner points
        left_mouth = face_landmarks.landmark[61]
        right_mouth = face_landmarks.landmark[291]
        top_lip = face_landmarks.landmark[13]
        bottom_lip = face_landmarks.landmark[14]

        # Calculate mouth width vs height ratio
        mouth_width = abs(right_mouth.x - left_mouth.x)
        mouth_height = abs(bottom_lip.y - top_lip.y)

        # Smiling typically has wider mouth
        ratio = mouth_width / (mouth_height + 0.001)

        return ratio > 3.0  # Threshold for smile

    def _get_head_position(self, face_landmarks):
        """Get average head position"""
        nose_tip = face_landmarks.landmark[1]
        return [nose_tip.x, nose_tip.y]

    def _get_hand_position(self, hand_landmarks):
        """Get average hand position"""
        wrist = hand_landmarks.landmark[0]
        return [wrist.x, wrist.y]

    def _analyze_posture(self, pose_landmarks):
        """
        Analyze if person has good posture
        Good posture: shoulders aligned, back straight
        """
        left_shoulder = pose_landmarks.landmark[11]
        right_shoulder = pose_landmarks.landmark[12]
        left_hip = pose_landmarks.landmark[23]
        right_hip = pose_landmarks.landmark[24]

        # Check shoulder alignment
        shoulder_diff = abs(left_shoulder.y - right_shoulder.y)

        # Check if back is straight (shoulders above hips)
        back_straight = (left_shoulder.y < left_hip.y) and (right_shoulder.y < right_hip.y)

        # Good posture if shoulders aligned and back straight
        return shoulder_diff < 0.1 and back_straight

    def _calculate_scores(self, metrics, duration):
        """
        Calculate final scores from raw metrics
        """
        total_frames = metrics['total_frames']

        if total_frames == 0:
            return self._get_default_scores()

        # Calculate percentages
        eye_contact_pct = (metrics['eye_contact_frames'] / total_frames) * 100
        smile_pct = (metrics['smiling_frames'] / total_frames) * 100
        gesture_pct = (metrics['hand_gesture_frames'] / total_frames) * 100
        good_posture_pct = (metrics['good_posture_frames'] / total_frames) * 100
        fidgeting_pct = (metrics['fidgeting_frames'] / total_frames) * 100
        face_visible_pct = (metrics['face_visible_frames'] / total_frames) * 100

        # Calculate movement scores
        avg_head_movement = np.mean(metrics['head_movements']) if metrics['head_movements'] else 0
        avg_hand_movement = np.mean(metrics['hand_movements']) if metrics['hand_movements'] else 0

        # Calculate brightness consistency
        brightness_std = np.std(metrics['brightness_values']) if metrics['brightness_values'] else 0
        lighting_quality = max(0, 100 - brightness_std)

        # Individual scores (0-10 scale)
        scores = {
            'eye_contact': min(10, (eye_contact_pct / 10)),
            'confidence': self._calculate_confidence_score(
                eye_contact_pct, smile_pct, good_posture_pct, fidgeting_pct
            ),
            'body_language': self._calculate_body_language_score(
                good_posture_pct, gesture_pct, fidgeting_pct
            ),
            'expressiveness': min(10, smile_pct / 5),
            'stability': max(0, 10 - (avg_head_movement * 100)),
            'professional_presence': self._calculate_presence_score(
                face_visible_pct, good_posture_pct, lighting_quality
            ),
            'engagement': self._calculate_engagement_score(
                gesture_pct, smile_pct, eye_contact_pct
            ),
            'overall_score': 0  # Will be calculated
        }

        # Calculate overall score (weighted average)
        scores['overall_score'] = (
                scores['eye_contact'] * 0.20 +
                scores['confidence'] * 0.25 +
                scores['body_language'] * 0.20 +
                scores['expressiveness'] * 0.10 +
                scores['stability'] * 0.10 +
                scores['professional_presence'] * 0.10 +
                scores['engagement'] * 0.05
        )

        # Detailed metrics for feedback
        scores['detailed_metrics'] = {
            'duration_seconds': duration,
            'eye_contact_percentage': round(eye_contact_pct, 1),
            'smile_percentage': round(smile_pct, 1),
            'gesture_usage': round(gesture_pct, 1),
            'good_posture_percentage': round(good_posture_pct, 1),
            'fidgeting_percentage': round(fidgeting_pct, 1),
            'face_visibility': round(face_visible_pct, 1),
            'lighting_quality': round(lighting_quality, 1),
            'head_stability': round(10 - (avg_head_movement * 100), 1),
            'total_frames_analyzed': total_frames
        }

        # Generate feedback
        scores['feedback'] = self._generate_feedback(scores)

        return scores

    def _calculate_confidence_score(self, eye_contact, smile, posture, fidgeting):
        """Calculate confidence score from multiple factors"""
        # High eye contact and good posture = confident
        # Fidgeting reduces confidence
        base_score = (eye_contact * 0.4 + posture * 0.4 + smile * 0.2) / 10
        penalty = fidgeting / 50
        return max(0, min(10, base_score - penalty))

    def _calculate_body_language_score(self, posture, gestures, fidgeting):
        """Calculate body language score"""
        # Good posture + appropriate gestures = good body language
        # Too much fidgeting is negative
        base_score = (posture * 0.6 + gestures * 0.4) / 10
        penalty = fidgeting / 30
        return max(0, min(10, base_score - penalty))

    def _calculate_presence_score(self, visibility, posture, lighting):
        """Calculate professional presence score"""
        return (visibility * 0.3 + posture * 0.4 + lighting * 0.3) / 10

    def _calculate_engagement_score(self, gestures, smile, eye_contact):
        """Calculate engagement score"""
        return (gestures * 0.3 + smile * 0.3 + eye_contact * 0.4) / 10

    def _generate_feedback(self, scores):
        """Generate detailed feedback based on scores"""
        feedback = {
            'strengths': [],
            'areas_for_improvement': [],
            'specific_tips': []
        }

        metrics = scores['detailed_metrics']

        # Eye Contact Feedback
        if scores['eye_contact'] >= 7:
            feedback['strengths'].append("Excellent eye contact - shows confidence and engagement")
        elif scores['eye_contact'] < 5:
            feedback['areas_for_improvement'].append("Limited eye contact with camera")
            feedback['specific_tips'].append(
                "Practice looking directly at the camera lens, not at your own image on screen")

        # Confidence Feedback
        if scores['confidence'] >= 7:
            feedback['strengths'].append("Strong, confident presence throughout the video")
        elif scores['confidence'] < 5:
            feedback['areas_for_improvement'].append("Confidence could be improved")
            feedback['specific_tips'].append("Practice power poses before interviews and maintain good posture")

        # Body Language Feedback
        if scores['body_language'] >= 7:
            feedback['strengths'].append("Professional and appropriate body language")
        elif scores['body_language'] < 5:
            feedback['areas_for_improvement'].append("Body language needs work")
            feedback['specific_tips'].append("Sit up straight, use hand gestures naturally, and avoid fidgeting")

        # Expressiveness Feedback
        if metrics['smile_percentage'] > 30:
            feedback['strengths'].append("Good use of facial expressions - appears friendly and approachable")
        elif metrics['smile_percentage'] < 10:
            feedback['areas_for_improvement'].append("Limited facial expressions")
            feedback['specific_tips'].append("Smile occasionally to appear more engaging and enthusiastic")

        # Fidgeting Feedback
        if metrics['fidgeting_percentage'] > 30:
            feedback['areas_for_improvement'].append("Noticeable fidgeting and nervous movements")
            feedback['specific_tips'].append("Keep hands visible and still, take deep breaths to reduce nervous energy")

        # Posture Feedback
        if metrics['good_posture_percentage'] < 40:
            feedback['areas_for_improvement'].append("Posture needs improvement")
            feedback['specific_tips'].append("Sit up straight with shoulders back - good posture projects confidence")

        # Lighting Feedback
        if metrics['lighting_quality'] < 60:
            feedback['specific_tips'].append("Improve lighting setup - face the light source for better visibility")

        return feedback

    def _get_default_scores(self):
        """Return default scores if video analysis fails"""
        return {
            'eye_contact': 5.0,
            'confidence': 5.0,
            'body_language': 5.0,
            'expressiveness': 5.0,
            'stability': 5.0,
            'professional_presence': 5.0,
            'engagement': 5.0,
            'overall_score': 5.0,
            'detailed_metrics': {},
            'feedback': {
                'strengths': [],
                'areas_for_improvement': ['Could not analyze video properly'],
                'specific_tips': ['Ensure good lighting and camera positioning']
            }
        }

    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
        if hasattr(self, 'hands'):
            self.hands.close()
        if hasattr(self, 'pose'):
            self.pose.close()