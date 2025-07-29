from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import json
import logging
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional, Any, Union
import uuid
from functools import wraps

# Supabase imports
from supabase import create_client, Client
import jwt
from dateutil import parser

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
analyzer = None
supabase: Optional[Client] = None

class SupabaseManager:
    def __init__(self, url: str, key: str):
        self.client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
    
    def create_user(self, email: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user and return user data with tokens"""
        try:
            user_data = {
                'email': email,
                'username': username,
                'display_name': username or (email.split('@')[0] if email else None),
                'plan_type': 'free'
            }
            
            # Remove None values
            user_data = {k: v for k, v in user_data.items() if v is not None}
            
            result = self.client.table('users').insert(user_data).execute()
            
            if result.data:
                user = result.data[0]
                # Assign default role
                self.client.table('user_roles').insert({
                    'user_id': user['user_id'],
                    'role': 'patient'
                }).execute()
                
                # Generate tokens
                tokens = self._generate_tokens(user['user_id'])
                
                return {
                    'user': user,
                    'tokens': tokens,
                    'success': True
                }
            else:
                return {'success': False, 'error': 'Failed to create user'}
                
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            result = self.client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.client.table('users').select('*').eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    def store_entry_and_analysis(self, user_id: str, entry_text: str, analysis_result: Dict[str, Any], 
                                mindweave_reflection: str, ysym_analysis: Optional[str] = None) -> bool:
        """Store entry and analysis results"""
        try:
            # Insert entry
            entry_data = {
                'user_id': user_id,
                'entry_text': entry_text
            }
            
            entry_result = self.client.table('entries').insert(entry_data).execute()
            
            if not entry_result.data:
                return False
                
            entry_id = entry_result.data[0]['entry_id']
            
            # Insert analysis
            analysis_data = {
                'entry_id': entry_id,
                'user_id': user_id,
                'emotions_quantified': analysis_result.get('emotions_quantified', {}),
                'emotion_polarity': analysis_result.get('emotion_polarity', {}),
                'topics': analysis_result.get('topics', []),
                'mindweave_reflection': mindweave_reflection,
                'ysym_triggered': analysis_result.get('emotion_polarity', {}).get('negative', 0) >= 0.6,
                'ysym_analysis': ysym_analysis,
                'analysis_version': '0.2.0'
            }
            
            analysis_result_db = self.client.table('analyses').insert(analysis_data).execute()
            
            return bool(analysis_result_db.data)
            
        except Exception as e:
            logger.error(f"Error storing entry and analysis: {str(e)}")
            return False
    
    def get_user_historical_entries(self, user_id: str, days_back: int = 21) -> List[Dict[str, Any]]:
        """Get user's historical entries for MindWeave analysis"""
        try:
            # Use the database function we created
            result = self.client.rpc('get_user_entries_in_range', {
                'p_user_id': user_id,
                'p_days_back': days_back
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting historical entries: {str(e)}")
            return []
    
    def search_user_entries(self, user_id: str, search_query: Optional[str] = None,
                          start_date: Optional[str] = None, end_date: Optional[str] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Search user entries"""
        try:
            params = {
                'p_user_id': user_id,
                'p_search_query': search_query,
                'p_start_date': start_date,
                'p_end_date': end_date,
                'p_limit': limit
            }
            
            result = self.client.rpc('search_user_entries', params).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error searching entries: {str(e)}")
            return []
    
    def _generate_tokens(self, user_id: str) -> Dict[str, str]:
        """Generate JWT tokens for user"""
        try:
            # Create refresh token
            refresh_token = str(uuid.uuid4())
            
            # Store refresh token in database
            session_data = {
                'user_id': user_id,
                'refresh_token': refresh_token,
                'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            self.client.table('user_sessions').insert(session_data).execute()
            
            # Generate JWT access token
            access_token_payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow(),
                'type': 'access'
            }
            
            access_token = jwt.encode(
                access_token_payload, 
                os.getenv('JWT_SECRET', 'fallback-secret-key'), 
                algorithm='HS256'
            )
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            
        except Exception as e:
            logger.error(f"Error generating tokens: {str(e)}")
            return {}

class GeminiAnalyzer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        os.environ['GEMINI_API_KEY'] = api_key
        self.client = genai.Client()
        logger.info("Gemini API client initialized successfully")
    
    def analyze_emotions_and_topics(self, entry_text: str) -> Dict[str, Any]:
        """First Gemini API call: Analyze emotions, topics, and quantify emotions"""
        prompt = f"""
        You are an expert emotion and topic analyzer. Analyze the following journal entry and provide quantified emotions and topics.
        
        Text to analyze: "{entry_text}"
        
        Please respond in the following JSON format:
        {{
            "emotions_quantified": {{"emotion1": 0.4, "emotion2": 0.6}},
            "emotion_polarity": {{"positive": 0.4, "negative": 0.6}},
            "topics": ["topic1", "topic2"]
        }}
        
        Guidelines:
        - emotions_quantified: Use specific emotion words with decimal values that sum to 1.0
        - emotion_polarity: Calculate the sum of positive vs negative emotions (must sum to 1.0)
        - For emotion_polarity, classify each emotion as positive or negative, then sum their values
        - emotions: Use words like happy, sad, anxious, calm, excited, proud, frustrated, overwhelmed, grateful, content, peaceful, stressed, hopeful, disappointed, etc.
        - topics: Use broad categories like family, work, exercise, relationships, health, travel, social, personal_growth, hobbies, finance, education, etc.
        - Ensure all emotion values are between 0 and 1 and sum to exactly 1.0
        - Be specific and accurate with emotions
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            
            response_text = response.text.strip()
            logger.info(f"Raw emotion analysis response: {response_text}")
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
            else:
                parsed_response = json.loads(response_text)
            
            emotions_quantified = parsed_response.get('emotions_quantified', {})
            emotion_polarity = parsed_response.get('emotion_polarity', {})
            topics = parsed_response.get('topics', [])
            
            # Validate and normalize emotions
            total_emotions = sum(emotions_quantified.values())
            if abs(total_emotions - 1.0) > 0.01:
                emotions_quantified = {k: v/total_emotions for k, v in emotions_quantified.items()}
            
            # Validate and normalize polarity
            total_polarity = sum(emotion_polarity.values())
            if abs(total_polarity - 1.0) > 0.01:
                emotion_polarity = {k: v/total_polarity for k, v in emotion_polarity.items()}
            
            return {
                'entry_text': entry_text,
                'emotions_quantified': emotions_quantified,
                'emotion_polarity': emotion_polarity,
                'topics': topics[:3],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            return self._fallback_analysis(entry_text)
    
    def generate_mindweave_reflection(self, entry_text: str, analysis_result: Dict[str, Any], 
                                    historical_entries: List[Dict[str, Any]] = None, 
                                    is_guest_mode: bool = False) -> str:
        """Second Gemini API call: Generate MindWeave reflection"""
        emotions_str = ", ".join([f"{emotion}: {value:.2f}" for emotion, value in analysis_result.get('emotions_quantified', {}).items()])
        topics_str = ", ".join(analysis_result.get('topics', []))
        
        # Different prompts for guest vs user mode
        if is_guest_mode or not historical_entries:
            # Guest mode: simplified reflection without historical context
            prompt = f"""
            You are analyzing a journal entry for immediate insights. Provide a thoughtful reflection without referencing past patterns.

            **Entry to analyze:** "{entry_text}"
            **Detected emotions:** {emotions_str}
            **Topics:** {topics_str}

            **Guidelines for guest mode reflection:**
            - Focus on the current entry only
            - Provide general emotional insights
            - Be supportive and understanding
            - Don't mention historical patterns or past entries
            - Keep it encouraging and actionable
            - 2-3 sentences maximum

            **Example format:**
            "This entry reveals [insight about current emotions/situation]. [Observation about what might be driving these feelings]. [Gentle insight or perspective]."

            Generate a thoughtful reflection:
            """
        else:
            # User mode: full MindWeave with historical context
            historical_summary = self._create_historical_summary(historical_entries)
            
            prompt = f"""
            You are a pattern recognition engine for MindWeave Reflections. Use historical data to identify behavioral and emotional patterns.

            **Current entry:** "{entry_text}"
            **Current emotions:** {emotions_str}
            **Topics:** {topics_str}

            **Historical context (past 21 days):**
            {historical_summary}

            **Tone Guidelines:**
            - Direct but not harsh
            - Observational, not prescriptive
            - State patterns, don't give advice
            - Mention specific numbers from history
            - Precise language - no fluff

            **Structure Formula:**
            1. Connect to historical pattern
            2. Reveal what this shows about behavior/thinking
            3. State the insight without judgment

            **Examples:**
            - "This is your 4th entry about presentation anxiety this month. Each time, the worry starts 2-3 days early despite past successes."
            - "You've mentioned feeling 'behind' in 7 of your last 12 entries, even when describing completed tasks."

            Generate a MindWeave reflection based on patterns:
            """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error in MindWeave reflection: {str(e)}")
            if is_guest_mode:
                return "Your entry shows meaningful emotional awareness. Consider tracking your patterns over time for deeper insights."
            else:
                return "Pattern analysis temporarily unavailable. Your entry has been recorded for future insights."
    
    def generate_ysym_analysis(self, entry_text: str, analysis_result: Dict[str, Any]) -> str:
        """Third Gemini API call: YSYM analysis (same for both modes)"""
        emotions_str = ", ".join([f"{emotion}: {value:.2f}" for emotion, value in analysis_result.get('emotions_quantified', {}).items()])
        negative_percentage = analysis_result.get('emotion_polarity', {}).get('negative', 0) * 100
        
        prompt = f"""
        You are analyzing the gap between surface statements and underlying emotions for "You Said You Meant" feature.
        
        **Context:**
        - Entry: "{entry_text}"
        - Emotions: {emotions_str}
        - Negative emotion level: {negative_percentage:.1f}% (triggered because ≥60%)
        
        **Your task:** Reveal the deeper emotional truth behind what the person said.
        
        **Format:** "You said: [surface statement] → You meant: [deeper emotional truth]"
        
        **Common deeper patterns:**
        - Control fears: "I forgot to..." → "I'm afraid of losing control"
        - Abandonment fears: "They didn't respond" → "I'm afraid of being rejected"
        - Perfectionism: "I'm behind" → "My standards keep moving and I'll never be enough"
        - Inadequacy: "I failed at..." → "I'm fundamentally flawed"
        
        Generate the YSYM analysis:
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error in YSYM analysis: {str(e)}")
            return "Deep analysis temporarily unavailable. Your patterns suggest underlying emotional needs worth exploring."
    
    def _create_historical_summary(self, historical_entries: List[Dict[str, Any]]) -> str:
        """Create a summary of historical entries for context"""
        if not historical_entries:
            return "No historical entries available."
        
        summary_parts = []
        
        # Count entries
        summary_parts.append(f"Total entries in past 21 days: {len(historical_entries)}")
        
        # Extract emotion patterns
        all_emotions = {}
        all_topics = []
        
        for entry in historical_entries:
            if entry.get('emotions_quantified'):
                for emotion, value in entry['emotions_quantified'].items():
                    all_emotions[emotion] = all_emotions.get(emotion, 0) + value
            
            if entry.get('topics'):
                all_topics.extend(entry['topics'])
        
        # Top emotions
        if all_emotions:
            top_emotions = sorted(all_emotions.items(), key=lambda x: x[1], reverse=True)[:3]
            emotions_summary = ", ".join([f"{emotion} ({count:.1f})" for emotion, count in top_emotions])
            summary_parts.append(f"Most frequent emotions: {emotions_summary}")
        
        # Top topics
        if all_topics:
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            topics_summary = ", ".join([f"{topic} ({count})" for topic, count in top_topics])
            summary_parts.append(f"Most frequent topics: {topics_summary}")
        
        return " | ".join(summary_parts)
    
    def _fallback_analysis(self, entry_text: str) -> Dict[str, Any]:
        """Fallback analysis when API calls fail"""
        return {
            'entry_text': entry_text,
            'emotions_quantified': {"neutral": 1.0},
            'emotion_polarity': {"positive": 0.5, "negative": 0.5},
            'topics': ["general"],
            'timestamp': datetime.now().isoformat()
        }

def get_analyzer():
    global analyzer
    if analyzer is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        analyzer = GeminiAnalyzer(api_key)
    return analyzer

def get_supabase():
    global supabase
    if supabase is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        if not url or not key:
            logger.warning("Supabase credentials not found - running in guest-only mode")
            return None
        supabase = SupabaseManager(url, key)
    return supabase

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, os.getenv('JWT_SECRET', 'fallback-secret-key'), algorithms=['HS256'])
            request.user_id = payload['user_id']
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated_function

# Routes
# 更新 main.py 中的主頁路由
@app.route('/')
def home():
    return jsonify({
        "service": "MindWeave Reflection Backend API",
        "version": "0.2.0",
        "status": "production",
        "author": "Gary Yang (gary@agryyang.in)",
        "repository": "https://github.com/Gary0302/Mind_BE",
        "documentation": {
            "quick_start": {
                "health_check": "GET /api/health",
                "guest_analysis": "POST /api/analyze",
                "user_registration": "POST /api/auth/register"
            },
            "authentication": {
                "register": {
                    "method": "POST",
                    "endpoint": "/api/auth/register",
                    "body": {
                        "email": "user@example.com (optional)",
                        "username": "username123 (optional, at least one required)"
                    },
                    "response": {
                        "user": "User object with user_id, email, username, etc.",
                        "tokens": {
                            "access_token": "JWT token for authenticated requests",
                            "refresh_token": "Token for refreshing access token"
                        }
                    }
                },
                "login": {
                    "method": "POST", 
                    "endpoint": "/api/auth/login",
                    "body": {"email": "user@example.com"},
                    "response": "Same format as registration"
                }
            },
            "analysis": {
                "guest_mode": {
                    "method": "POST",
                    "endpoint": "/api/analyze",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"entry_text": "Your journal entry (max 5000 chars)"},
                    "response": {
                        "analysis": "Emotion quantification and topics",
                        "mindweave_reflection": "AI-generated insight",
                        "ysym": "Boolean - triggers when negative emotions >= 60%",
                        "ysym_analysis": "Deeper emotional analysis (if triggered)",
                        "mode": "guest",
                        "stored": False
                    }
                },
                "user_mode": {
                    "method": "POST",
                    "endpoint": "/api/analyze", 
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer your_access_token"
                    },
                    "body": {
                        "entry_text": "Your journal entry",
                        "user_id": "your_user_id"
                    },
                    "response": {
                        "analysis": "Same as guest mode",
                        "mindweave_reflection": "Enhanced with historical context",
                        "mode": "user",
                        "stored": True,
                        "historical_entries_used": "Number of past entries analyzed"
                    }
                }
            },
            "search": {
                "method": "POST",
                "endpoint": "/api/search",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer your_access_token"
                },
                "body": {
                    "search_query": "keyword (optional)",
                    "start_date": "YYYY-MM-DD (optional)",
                    "end_date": "YYYY-MM-DD (optional)", 
                    "limit": "number (optional, max 100)"
                },
                "response": {
                    "results": "Array of matching entries with analysis",
                    "count": "Number of results",
                    "search_params": "Echo of search parameters"
                }
            },
            "user_management": {
                "profile": {
                    "method": "GET",
                    "endpoint": "/api/user/profile",
                    "headers": {"Authorization": "Bearer your_access_token"},
                    "response": {
                        "user": "User information",
                        "stats": "Usage statistics and insights"
                    }
                },
                "import_guest_data": {
                    "method": "POST",
                    "endpoint": "/api/user/import-guest-data",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer your_access_token"
                    },
                    "body": {
                        "analyses": "Array of previous guest analyses to import"
                    }
                }
            }
        },
        "features": {
            "dual_mode_analysis": "Both guest and authenticated user modes",
            "emotion_quantification": "Precise numerical emotion analysis (sum = 1.0)",
            "historical_pattern_recognition": "AI analyzes 14-21 days of past entries",
            "ysym_analysis": "You Said You Meant - reveals deeper emotions", 
            "smart_triggering": "YSYM activates when negative emotions >= 60%",
            "full_text_search": "Search entries with relevance scoring",
            "data_persistence": "Secure storage with Row Level Security"
        },
        "response_times": {
            "guest_mode": "1.5-3 seconds",
            "user_mode": "3-5 seconds (includes historical analysis)",
            "search": "200-500ms",
            "authentication": "100-300ms"
        },
        "limits": {
            "max_entry_length": 5000,
            "ysym_trigger_threshold": 0.6,
            "max_search_results": 100,
            "historical_days_default": 21
        },
        "examples": {
            "curl_guest_analysis": 'curl -X POST https://mind-be-ruddy.vercel.app/api/analyze -H "Content-Type: application/json" -d \'{"entry_text": "I feel great today!"}\'',
            "curl_registration": 'curl -X POST https://mind-be-ruddy.vercel.app/api/auth/register -H "Content-Type: application/json" -d \'{"email": "test@example.com", "username": "testuser"}\'',
            "curl_user_analysis": 'curl -X POST https://mind-be-ruddy.vercel.app/api/analyze -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d \'{"entry_text": "Today was stressful", "user_id": "YOUR_USER_ID"}\'',
            "curl_search": 'curl -X POST https://mind-be-ruddy.vercel.app/api/search -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d \'{"search_query": "anxious", "limit": 10}\''
        },
        "error_handling": {
            "400": "Bad Request - Invalid input or missing required fields",
            "401": "Unauthorized - Invalid or missing authentication token", 
            "500": "Internal Server Error - Temporary service issues",
            "example_error": {
                "error": "entry_text field is required",
                "status": "error"
            }
        },
        "integration_tips": {
            "rate_limiting": "Implement 3-second debounce on analysis requests",
            "error_handling": "Always check response.ok before processing data",
            "token_management": "Store refresh tokens securely, access tokens have 24h expiry",
            "offline_support": "Consider queuing requests when network is unavailable",
            "user_experience": "Show loading states during analysis (3-5 second processing time)"
        },
        "support": {
            "issues": "https://github.com/Gary0302/Mind_BE/issues",
            "email": "gary@agryyang.in",
            "documentation": "See README.md for detailed integration guides"
        },
        "environment": "vercel",
        "database": "supabase_postgresql",
        "ai_provider": "google_gemini",
        "license": "MIT (will be updated in next version)",
        "next_version_notes": {
            "license_change": "New license terms will be applied",
            "environment_variables": "Prompts will be configurable via environment variables",
            "enhanced_features": "Weekly reviews and therapist mode"
        }
    })

@app.route('/api/health')
def health_check():
    supabase_status = "connected" if get_supabase() else "not configured"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mindweave-reflection-backend",
        "version": "0.2.0",
        "environment": "vercel",
        "integrations": {
            "gemini": "connected",
            "supabase": supabase_status
        }
    })

# 添加到 main.py 中的調試端點
@app.route('/api/debug/supabase')
def debug_supabase():
    """Debug endpoint to check Supabase connection and tables"""
    try:
        db = get_supabase()
        if not db:
            return jsonify({
                "error": "Supabase client not initialized",
                "env_vars": {
                    "SUPABASE_URL": "set" if os.getenv('SUPABASE_URL') else "missing",
                    "SUPABASE_ANON_KEY": "set" if os.getenv('SUPABASE_ANON_KEY') else "missing",
                    "JWT_SECRET": "set" if os.getenv('JWT_SECRET') else "missing"
                }
            }), 500
        
        # Test basic connection
        try:
            # Try a simple query
            result = db.client.table('users').select('count').execute()
            tables_exist = True
        except Exception as e:
            tables_exist = False
            table_error = str(e)
        
        return jsonify({
            "supabase_client": "initialized",
            "tables_exist": tables_exist,
            "table_error": table_error if not tables_exist else None,
            "env_vars": {
                "SUPABASE_URL": "set" if os.getenv('SUPABASE_URL') else "missing",
                "SUPABASE_ANON_KEY": "set" if os.getenv('SUPABASE_ANON_KEY') else "missing", 
                "JWT_SECRET": "set" if os.getenv('JWT_SECRET') else "missing"
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Debug error: {str(e)}",
            "env_vars": {
                "SUPABASE_URL": "set" if os.getenv('SUPABASE_URL') else "missing",
                "SUPABASE_ANON_KEY": "set" if os.getenv('SUPABASE_ANON_KEY') else "missing",
                "JWT_SECRET": "set" if os.getenv('JWT_SECRET') else "missing"
            }
        }), 500

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username')
        
        if not email and not username:
            return jsonify({"error": "Either email or username is required"}), 400
        
        # Check if user already exists
        if email and db.get_user_by_email(email):
            return jsonify({"error": "User with this email already exists"}), 409
        
        result = db.create_user(email=email, username=username)
        
        if result['success']:
            return jsonify({
                "user": result['user'],
                "tokens": result['tokens'],
                "message": "User created successfully"
            })
        else:
            return jsonify({"error": result['error']}), 400
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        user = db.get_user_by_email(email)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        tokens = db._generate_tokens(user['user_id'])
        
        return jsonify({
            "user": user,
            "tokens": tokens,
            "message": "Login successful"
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

# Main analysis endpoint
@app.route('/api/analyze', methods=['POST'])
def analyze_entry():
    start_time = datetime.now()
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data or 'entry_text' not in data:
            return jsonify({"error": "entry_text field is required"}), 400
        
        entry_text = data['entry_text']
        if not isinstance(entry_text, str) or not entry_text.strip():
            return jsonify({"error": "entry_text must be a non-empty string"}), 400
        
        entry_text = entry_text.strip()
        if len(entry_text) > 5000:
            return jsonify({"error": "entry_text too long (max 5000 characters)"}), 400
        
        # Check if user_id is provided (user mode vs guest mode)
        user_id = data.get('user_id')
        is_guest_mode = user_id is None
        
        # Initialize variables
        historical_entries = []
        stored = False
        
        analyzer_instance = get_analyzer()
        db = get_supabase()
        
        # First API call: Emotion and topic analysis
        logger.info(f"Starting analysis - Mode: {'guest' if is_guest_mode else 'user'}")
        analysis_result = analyzer_instance.analyze_emotions_and_topics(entry_text)
        
        # Get historical context for user mode
        if not is_guest_mode and db:
            try:
                historical_entries = db.get_user_historical_entries(user_id, days_back=21)
                logger.info(f"Retrieved {len(historical_entries)} historical entries")
            except Exception as e:
                logger.warning(f"Could not retrieve historical entries: {str(e)}")
        
        # Second API call: MindWeave reflection
        logger.info("Generating MindWeave reflection")
        mindweave_reflection = analyzer_instance.generate_mindweave_reflection(
            entry_text, 
            analysis_result, 
            historical_entries, 
            is_guest_mode
        )
        
        # Check YSYM trigger (same threshold for both modes)
        negative_ratio = analysis_result.get('emotion_polarity', {}).get('negative', 0)
        ysym_triggered = negative_ratio >= 0.6
        
        logger.info(f"Negative emotion ratio: {negative_ratio:.2f}, YSYM triggered: {ysym_triggered}")
        
        # Prepare response data
        response_data = {
            "analysis": analysis_result,
            "mindweave_reflection": mindweave_reflection,
            "ysym": ysym_triggered,
            "mode": "guest" if is_guest_mode else "user",
            "stored": False,
            "status": "success"
        }
        
        # Add mode-specific information
        if is_guest_mode:
            response_data["message"] = "Analysis complete! Register to unlock historical insights and pattern tracking."
            response_data["benefits"] = [
                "Track emotional patterns over time",
                "Get insights based on your history",
                "Search through past entries",
                "Weekly and monthly reviews"
            ]
        else:
            response_data["historical_entries_used"] = len(historical_entries)
        
        # Third API call: YSYM analysis (if triggered)
        if ysym_triggered:
            logger.info("Generating YSYM analysis")
            ysym_analysis = analyzer_instance.generate_ysym_analysis(entry_text, analysis_result)
            response_data["ysym_analysis"] = ysym_analysis
        
        # Store data for user mode
        if not is_guest_mode and db:
            try:
                stored = db.store_entry_and_analysis(
                    user_id, 
                    entry_text, 
                    analysis_result, 
                    mindweave_reflection, 
                    response_data.get("ysym_analysis")
                )
                response_data["stored"] = stored
                if stored:
                    logger.info("Entry and analysis stored successfully")
                else:
                    logger.warning("Failed to store entry and analysis")
            except Exception as e:
                logger.error(f"Error storing data: {str(e)}")
                response_data["storage_error"] = "Failed to save data, but analysis completed"
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        response_data["processing_time"] = round(processing_time, 2)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing entry: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "status": "error"
        }), 500

# Search endpoint
@app.route('/api/search', methods=['POST'])
@require_auth
def search_entries():
    try:
        db = get_supabase()
        if not db:
            return jsonify({"error": "Database not available"}), 503
        
        data = request.get_json()
        user_id = request.user_id  # From auth decorator
        
        # Extract search parameters
        search_query = data.get('search_query')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        limit = min(data.get('limit', 50), 100)  # Max 100 results
        
        # Validate date format if provided
        if start_date:
            try:
                parser.parse(start_date)
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
        
        if end_date:
            try:
                parser.parse(end_date)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
        
        # Perform search
        results = db.search_user_entries(
            user_id=user_id,
            search_query=search_query,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return jsonify({
            "results": results,
            "count": len(results),
            "search_params": {
                "query": search_query,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            },
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": "Search failed", "message": str(e)}), 500

# Test endpoint
@app.route('/api/test')
def test_endpoint():
    sample_entry = "I stayed up until 3am working on my startup again. I know I shouldn't but I feel so behind on everything. Sarah didn't reply to my message either, which makes me think she's avoiding me."
    
    try:
        analyzer_instance = get_analyzer()
        
        # Test guest mode
        logger.info("Testing guest mode analysis")
        analysis_result = analyzer_instance.analyze_emotions_and_topics(sample_entry)
        mindweave_reflection = analyzer_instance.generate_mindweave_reflection(
            sample_entry, analysis_result, None, True
        )
        
        negative_ratio = analysis_result.get('emotion_polarity', {}).get('negative', 0)
        ysym_triggered = negative_ratio >= 0.6
        
        response_data = {
            "test_mode": "guest",
            "analysis": analysis_result,
            "mindweave_reflection": mindweave_reflection,
            "ysym": ysym_triggered,
            "status": "success",
            "sample_entry": sample_entry,
            "database_status": "connected" if get_supabase() else "not configured"
        }
        
        if ysym_triggered:
            ysym_analysis = analyzer_instance.generate_ysym_analysis(sample_entry, analysis_result)
            response_data["ysym_analysis"] = ysym_analysis
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        return jsonify({"error": str(e), "status": "error"}), 500

# User management endpoints
@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    try:
        db = get_supabase()
        if not db:
            return jsonify({"error": "Database not available"}), 503
        
        user = db.get_user_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user stats
        try:
            historical_entries = db.get_user_historical_entries(request.user_id, days_back=30)
            total_entries = len(historical_entries)
            
            # Calculate basic stats
            recent_emotions = {}
            recent_topics = []
            
            for entry in historical_entries:
                if entry.get('emotions_quantified'):
                    for emotion, value in entry['emotions_quantified'].items():
                        recent_emotions[emotion] = recent_emotions.get(emotion, 0) + value
                
                if entry.get('topics'):
                    recent_topics.extend(entry['topics'])
            
            stats = {
                "total_entries_30_days": total_entries,
                "top_emotions": dict(sorted(recent_emotions.items(), key=lambda x: x[1], reverse=True)[:5]),
                "top_topics": list(set(recent_topics))[:5]
            }
            
        except Exception as e:
            logger.warning(f"Could not calculate stats: {str(e)}")
            stats = {"total_entries_30_days": 0}
        
        return jsonify({
            "user": user,
            "stats": stats,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return jsonify({"error": "Could not fetch profile"}), 500

# Import guest data endpoint
@app.route('/api/user/import-guest-data', methods=['POST'])
@require_auth
def import_guest_data():
    """Import previously analyzed data from guest mode"""
    try:
        db = get_supabase()
        if not db:
            return jsonify({"error": "Database not available"}), 503
        
        data = request.get_json()
        guest_analyses = data.get('analyses', [])
        
        if not isinstance(guest_analyses, list):
            return jsonify({"error": "analyses must be a list"}), 400
        
        imported_count = 0
        failed_count = 0
        
        for analysis_data in guest_analyses:
            try:
                # Validate required fields
                if not all(key in analysis_data for key in ['entry_text', 'analysis', 'mindweave_reflection']):
                    failed_count += 1
                    continue
                
                # Store entry and analysis
                success = db.store_entry_and_analysis(
                    user_id=request.user_id,
                    entry_text=analysis_data['entry_text'],
                    analysis_result=analysis_data['analysis'],
                    mindweave_reflection=analysis_data['mindweave_reflection'],
                    ysym_analysis=analysis_data.get('ysym_analysis')
                )
                
                if success:
                    imported_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to import one analysis: {str(e)}")
                failed_count += 1
        
        return jsonify({
            "imported": imported_count,
            "failed": failed_count,
            "total_provided": len(guest_analyses),
            "status": "success" if imported_count > 0 else "failed"
        })
        
    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        return jsonify({"error": "Import failed"}), 500

# Utility endpoints
@app.route('/api/version')
def version_info():
    return jsonify({
        "version": "0.2.0",
        "author": "Gary (gary@agryyang.in)",
        "repository": "https://github.com/Gary0302/Mind_BE",
        "features": {
            "dual_mode_analysis": True,
            "historical_patterns": True,
            "entry_search": True,
            "ysym_analysis": True,
            "guest_data_import": True,
            "therapist_mode": "planned"
        },
        "api_limits": {
            "max_entry_length": 5000,
            "ysym_trigger_threshold": 0.6,
            "max_search_results": 100,
            "historical_days_default": 21
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "auth": ["/api/auth/register", "/api/auth/login"],
            "analysis": ["/api/analyze", "/api/search"],
            "user": ["/api/user/profile", "/api/user/import-guest-data"],
            "utility": ["/api/health", "/api/test", "/api/version"]
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500

# Vercel handler
app_handler = app

if __name__ == '__main__':
    # Load environment variables for local development
    from dotenv import load_dotenv
    load_dotenv()
    
    app.run(debug=True, port=5050)