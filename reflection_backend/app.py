# mind_backend/app.py
"""
Reflection Backend API using Gemini AI for emotion analysis and reflection generation.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EmotionAnalysisResult:
    """Data class for emotion analysis results."""
    entry_text: str
    emotions: List[str]
    topics: List[str]
    timestamp: str


class GeminiAnalyzer:
    """Handler for Gemini AI API interactions."""
    
    def __init__(self, api_key: str) -> None:
        """Initialize Gemini API client."""
        if not api_key:
            raise ValueError("API key is required")
        
        # The client automatically gets the API key from GEMINI_API_KEY environment variable
        # but we can also pass it explicitly
        os.environ['GEMINI_API_KEY'] = api_key
        self.client = genai.Client()
        logger.info("Gemini API client initialized successfully")
    
    def analyze_emotions_and_topics(self, entry_text: str) -> EmotionAnalysisResult:
        """
        First Gemini API call: Extract emotions and topics from entry.
        
        Args:
            entry_text: The journal entry text to analyze
            
        Returns:
            EmotionAnalysisResult with extracted emotions and topics
        """
        prompt = self._create_analysis_prompt(entry_text)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking for speed
                )
            )
            result_text = response.text.strip()
            
            # Clean and parse JSON response
            result_text = self._clean_json_response(result_text)
            parsed_result = json.loads(result_text)
            
            emotions = parsed_result.get('emotions', ['neutral'])
            topics = parsed_result.get('topics', ['general'])
            
            # Validate and clean results
            emotions = self._validate_emotions(emotions)
            topics = self._validate_topics(topics)
            
            logger.info(f"Analysis completed - Emotions: {emotions}, Topics: {topics}")
            
            return EmotionAnalysisResult(
                entry_text=entry_text,
                emotions=emotions,
                topics=topics,
                timestamp=datetime.now().isoformat()
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}, Response: {result_text}")
            return self._fallback_parse(entry_text, result_text)
        except Exception as e:
            logger.error(f"Error in emotion analysis: {str(e)}")
            return self._create_fallback_result(entry_text)
    
    def generate_reflection(
        self, 
        entry_text: str, 
        analysis_result: EmotionAnalysisResult
    ) -> str:
        """
        Second Gemini API call: Generate reflection based on entry and analysis.
        
        Args:
            entry_text: Original journal entry
            analysis_result: Results from emotion/topic analysis
            
        Returns:
            Generated reflection text
        """
        prompt = self._create_reflection_prompt(entry_text, analysis_result)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking for speed
                )
            )
            reflection = response.text.strip()
            logger.info("Reflection generated successfully")
            return reflection
        except Exception as e:
            logger.error(f"Error in reflection generation: {str(e)}")
            return self._create_fallback_reflection()
    
    def _create_analysis_prompt(self, entry_text: str) -> str:
        """Create the prompt for emotion and topic analysis."""
        return f"""
        You are an expert emotion and topic analyzer. Analyze the following text and extract emotions and topics.

        Text to analyze: "{entry_text}"

        Please respond in the following JSON format:
        {{
            "emotions": ["emotion1", "emotion2", "emotion3"],
            "topics": ["topic1", "topic2"]
        }}

        Guidelines:
        - emotions: Use common emotion words like happy, sad, anxious, calm, excited, proud, frustrated, overwhelmed, grateful, content, etc.
        - topics: Use broad categories like family, work, exercise, relationships, health, travel, social, personal_growth, etc.
        - Return 1-4 emotions that best represent the text
        - Return 1-3 topics that best categorize the content
        - Only return valid JSON, no additional text
        """
    
    def _create_reflection_prompt(
        self, 
        entry_text: str, 
        analysis_result: EmotionAnalysisResult
    ) -> str:
        """Create the prompt for reflection generation."""
        return f"""
        You are a compassionate life coach and therapist. Based on the journal entry and emotional analysis below, create a thoughtful, empathetic reflection.

        Original Entry: "{entry_text}"
        Detected Emotions: {analysis_result.emotions}
        Detected Topics: {analysis_result.topics}
        
        Please create a reflection that:
        1. Acknowledges the emotions the person is experiencing
        2. Provides gentle insights about the situation
        3. Offers perspective, encouragement, or gentle advice where appropriate
        4. Is supportive, warm, and non-judgmental
        5. Is 2-4 sentences long
        6. Feels personal and human, not robotic
        
        Write the reflection directly without any formatting or labels:
        """
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean JSON response from potential markdown formatting."""
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        return response_text.strip()
    
    def _validate_emotions(self, emotions: List[str]) -> List[str]:
        """Validate and filter emotions."""
        valid_emotions = [
            'happy', 'sad', 'anxious', 'calm', 'excited', 'proud', 'frustrated',
            'overwhelmed', 'grateful', 'content', 'stressed', 'relaxed', 'worried',
            'confident', 'confused', 'angry', 'peaceful', 'hopeful', 'disappointed',
            'motivated', 'tired', 'energetic', 'lonely', 'loved', 'fearful',
            'optimistic', 'pessimistic', 'curious', 'satisfied', 'nervous'
        ]
        
        filtered_emotions = [
            emotion.lower().strip() for emotion in emotions 
            if isinstance(emotion, str) and emotion.lower().strip() in valid_emotions
        ]
        
        return filtered_emotions if filtered_emotions else ['neutral']
    
    def _validate_topics(self, topics: List[str]) -> List[str]:
        """Validate and filter topics."""
        valid_topics = [
            'family', 'work', 'exercise', 'relationships', 'health', 'travel',
            'social', 'personal_growth', 'education', 'finances', 'hobbies',
            'spiritual', 'career', 'creativity', 'nature', 'technology',
            'food', 'entertainment', 'home', 'friends', 'goals', 'challenges'
        ]
        
        filtered_topics = [
            topic.lower().strip() for topic in topics 
            if isinstance(topic, str) and topic.lower().strip() in valid_topics
        ]
        
        return filtered_topics if filtered_topics else ['general']
    
    def _fallback_parse(self, entry_text: str, response_text: str) -> EmotionAnalysisResult:
        """Fallback method for parsing non-JSON responses."""
        emotions = ['neutral']
        topics = ['general']
        
        # Try to extract emotions and topics using regex
        emotion_match = re.search(r'"emotions":\s*\[(.*?)\]', response_text)
        topic_match = re.search(r'"topics":\s*\[(.*?)\]', response_text)
        
        if emotion_match:
            emotions_str = emotion_match.group(1)
            emotions = [
                e.strip().strip('"').strip("'") 
                for e in emotions_str.split(',') 
                if e.strip()
            ]
        
        if topic_match:
            topics_str = topic_match.group(1)
            topics = [
                t.strip().strip('"').strip("'") 
                for t in topics_str.split(',') 
                if t.strip()
            ]
        
        return EmotionAnalysisResult(
            entry_text=entry_text,
            emotions=self._validate_emotions(emotions),
            topics=self._validate_topics(topics),
            timestamp=datetime.now().isoformat()
        )
    
    def _create_fallback_result(self, entry_text: str) -> EmotionAnalysisResult:
        """Create fallback result when analysis fails."""
        return EmotionAnalysisResult(
            entry_text=entry_text,
            emotions=['neutral'],
            topics=['general'],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_fallback_reflection(self) -> str:
        """Create fallback reflection when generation fails."""
        return ("Thank you for sharing your thoughts. Every experience contributes "
                "to your personal growth journey, and it's wonderful that you're "
                "taking time to reflect on your feelings.")


class ReflectionAPI:
    """Main Flask application class."""
    
    def __init__(self) -> None:
        """Initialize Flask app and Gemini analyzer."""
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize Gemini analyzer
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not found")
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.analyzer = GeminiAnalyzer(api_key)
        self._setup_routes()
        
        logger.info("Reflection API initialized successfully")
    
    def _setup_routes(self) -> None:
        """Setup all API routes."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy", 
                "timestamp": datetime.now().isoformat(),
                "service": "reflection-backend",
                "version": "0.1.0"
            })

        @self.app.route('/test', methods=['GET'])
        def test_endpoint():
            """Test endpoint with sample data."""
            sample_entry = ("Today I felt overwhelmed at work but managed to complete "
                          "my important project. I'm proud of what I accomplished "
                          "despite the stress.")
            
            try:
                analysis_result = self.analyzer.analyze_emotions_and_topics(sample_entry)
                reflection = self.analyzer.generate_reflection(sample_entry, analysis_result)
                
                return jsonify({
                    "sample_analysis": {
                        "entry_text": sample_entry,
                        "emotions": analysis_result.emotions,
                        "topics": analysis_result.topics,
                        "timestamp": analysis_result.timestamp
                    },
                    "sample_reflection": reflection,
                    "status": "success",
                    "message": "API is working correctly"
                })
            except Exception as e:
                logger.error(f"Test endpoint error: {str(e)}")
                return jsonify({
                    "error": str(e),
                    "status": "error"
                }), 500

        @self.app.route('/analyze', methods=['POST'])
        def analyze_entry():
            """Analyze single journal entry."""
            return self._handle_single_analysis()

        @self.app.route('/batch-analyze', methods=['POST'])
        def batch_analyze():
            """Analyze multiple journal entries."""
            return self._handle_batch_analysis()
    
    def _handle_single_analysis(self) -> tuple:
        """Handle single entry analysis."""
        start_time = datetime.now()
        
        try:
            # Validate request
            validation_error = self._validate_request()
            if validation_error:
                return validation_error
            
            data = request.get_json()
            entry_text = data['entry_text'].strip()
            
            logger.info(f"Processing entry: {entry_text[:100]}{'...' if len(entry_text) > 100 else ''}")
            
            # Analyze emotions and topics
            analysis_result = self.analyzer.analyze_emotions_and_topics(entry_text)
            
            # Generate reflection
            reflection = self.analyzer.generate_reflection(entry_text, analysis_result)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            response = {
                "analysis": {
                    "entry_text": analysis_result.entry_text,
                    "emotions": analysis_result.emotions,
                    "topics": analysis_result.topics,
                    "timestamp": analysis_result.timestamp
                },
                "reflection": reflection,
                "status": "success",
                "processing_time": round(processing_time, 2)
            }
            
            logger.info(f"Request processed successfully in {processing_time:.2f}s")
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"Error processing entry: {str(e)}")
            return jsonify({
                "error": "Internal server error",
                "message": str(e),
                "status": "error"
            }), 500
    
    def _handle_batch_analysis(self) -> tuple:
        """Handle batch analysis of multiple entries."""
        start_time = datetime.now()
        
        try:
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400
            
            data = request.get_json()
            
            if not data or 'entries' not in data:
                return jsonify({"error": "entries array is required"}), 400
            
            entries = data['entries']
            
            if not isinstance(entries, list):
                return jsonify({"error": "entries must be an array"}), 400
            
            if len(entries) > 10:
                return jsonify({"error": "Maximum 10 entries allowed per batch"}), 400
            
            results = []
            
            for i, entry_text in enumerate(entries):
                if not isinstance(entry_text, str) or not entry_text.strip():
                    logger.warning(f"Skipping empty or invalid entry at index {i}")
                    continue
                
                entry_text = entry_text.strip()
                
                if len(entry_text) > 5000:
                    logger.warning(f"Skipping too long entry at index {i}")
                    continue
                
                logger.info(f"Processing batch entry {i+1}/{len(entries)}")
                
                analysis_result = self.analyzer.analyze_emotions_and_topics(entry_text)
                reflection = self.analyzer.generate_reflection(entry_text, analysis_result)
                
                results.append({
                    "analysis": {
                        "entry_text": analysis_result.entry_text,
                        "emotions": analysis_result.emotions,
                        "topics": analysis_result.topics,
                        "timestamp": analysis_result.timestamp
                    },
                    "reflection": reflection
                })
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            response = {
                "results": results,
                "status": "success",
                "total_processed": len(results),
                "processing_time": round(processing_time, 2)
            }
            
            logger.info(f"Batch processed {len(results)} entries in {processing_time:.2f}s")
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return jsonify({
                "error": "Internal server error",
                "message": str(e),
                "status": "error"
            }), 500
    
    def _validate_request(self) -> Optional[tuple]:
        """Validate incoming request."""
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        if 'entry_text' not in data:
            return jsonify({"error": "entry_text field is required"}), 400
        
        entry_text = data['entry_text']
        
        if not isinstance(entry_text, str):
            return jsonify({"error": "entry_text must be a string"}), 400
        
        entry_text = entry_text.strip()
        
        if not entry_text:
            return jsonify({"error": "entry_text cannot be empty"}), 400
        
        if len(entry_text) > 5000:
            return jsonify({"error": "entry_text too long (max 5000 characters)"}), 400
        
        return None
    
    def run(self, debug: bool = True, host: str = '0.0.0.0', port: int = 5000) -> None:
        """Run the Flask application."""
        self.app.run(debug=debug, host=host, port=port)


def create_app() -> Flask:
    """Factory function to create Flask app."""
    api = ReflectionAPI()
    return api.app


def main() -> None:
    """Main entry point."""
    try:
        api = ReflectionAPI()
        print("🚀 Reflection Backend API Starting...")
        print("📋 Available Endpoints:")
        print("   GET  /health        - Health check")
        print("   GET  /test          - Test with sample data")
        print("   POST /analyze       - Analyze single entry")
        print("   POST /batch-analyze - Analyze multiple entries")
        print("🔑 Make sure GEMINI_API_KEY environment variable is set")
        print("🌐 Server starting on http://localhost:5000")
        
        api.run(debug=True, port=5050)
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("💡 Please set GEMINI_API_KEY environment variable:")
        print("   export GEMINI_API_KEY='your_api_key_here'")
    except Exception as e:
        print(f"❌ Server Error: {e}")


if __name__ == '__main__':
    main()