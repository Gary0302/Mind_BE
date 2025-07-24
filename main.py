from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import json
import logging
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
analyzer = None

class GeminiAnalyzer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        os.environ['GEMINI_API_KEY'] = api_key
        self.client = genai.Client()
        logger.info("Gemini API client initialized successfully")
    
    def analyze_emotions_and_topics(self, entry_text: str):
        prompt = f"""
        You are an expert emotion and topic analyzer. Analyze the following text and extract emotions and topics.
        Text to analyze: "{entry_text}"
        Please respond in the following JSON format:
        {{"emotions": ["emotion1", "emotion2"], "topics": ["topic1", "topic2"]}}
        Guidelines:
        - emotions: Use common emotion words like happy, sad, anxious, calm, excited, proud, frustrated, overwhelmed, grateful, content, etc.
        - topics: Use broad categories like family, work, exercise, relationships, health, travel, social, personal_growth, etc.
        - Return 1-4 emotions that best represent the text
        - Return 1-3 topics that best categorize the content
        - Only return valid JSON, no additional text
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            result_text = response.text.strip()
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            parsed_result = json.loads(result_text)
            emotions = parsed_result.get('emotions', ['neutral'])
            topics = parsed_result.get('topics', ['general'])
            
            return {
                'entry_text': entry_text,
                'emotions': emotions,
                'topics': topics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            return {
                'entry_text': entry_text,
                'emotions': ['neutral'],
                'topics': ['general'],
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_reflection(self, entry_text: str, analysis_result: dict) -> str:
        prompt = f"""
        You are a compassionate life coach and therapist. Based on the journal entry and emotional analysis below, create a thoughtful, empathetic reflection.
        Original Entry: "{entry_text}"
        Detected Emotions: {analysis_result['emotions']}
        Detected Topics: {analysis_result['topics']}
        Please create a reflection that:
        1. Acknowledges the emotions the person is experiencing
        2. Provides gentle insights about the situation
        3. Offers perspective, encouragement, or gentle advice where appropriate
        4. Is supportive, warm, and non-judgmental
        5. Is 2-4 sentences long
        6. Feels personal and human, not robotic
        Write the reflection directly without any formatting or labels:
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error in reflection generation: {str(e)}")
            return "Thank you for sharing your thoughts. Every experience contributes to your personal growth journey."

def get_analyzer():
    global analyzer
    if analyzer is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        analyzer = GeminiAnalyzer(api_key)
    return analyzer

@app.route('/')
def home():
    return jsonify({
        "message": "Reflection Backend API",
        "version": "0.1.0",
        "status": "running",
        "environment": "vercel",
        "endpoints": {
            "health": "/api/health",
            "test": "/api/test",
            "analyze": "/api/analyze (POST)",
            "batch_analyze": "/api/batch-analyze (POST)"
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "reflection-backend",
        "version": "0.1.0",
        "environment": "vercel"
    })

@app.route('/api/test')
def test_endpoint():
    sample_entry = "Today I felt overwhelmed at work but managed to complete my important project. I'm proud of what I accomplished despite the stress."
    
    try:
        analyzer_instance = get_analyzer()
        analysis_result = analyzer_instance.analyze_emotions_and_topics(sample_entry)
        reflection = analyzer_instance.generate_reflection(sample_entry, analysis_result)
        
        return jsonify({
            "sample_analysis": analysis_result,
            "sample_reflection": reflection,
            "status": "success",
            "message": "API is working correctly on Vercel"
        })
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_entry():
    start_time = datetime.now()
    
    try:
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
        
        analyzer_instance = get_analyzer()
        analysis_result = analyzer_instance.analyze_emotions_and_topics(entry_text)
        reflection = analyzer_instance.generate_reflection(entry_text, analysis_result)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return jsonify({
            "analysis": analysis_result,
            "reflection": reflection,
            "status": "success",
            "processing_time": round(processing_time, 2)
        })
        
    except Exception as e:
        logger.error(f"Error processing entry: {str(e)}")
        return jsonify({"error": "Internal server error", "message": str(e), "status": "error"}), 500

@app.route('/api/batch-analyze', methods=['POST'])
def batch_analyze():
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
        analyzer_instance = get_analyzer()
        
        for i, entry_text in enumerate(entries):
            if not isinstance(entry_text, str) or not entry_text.strip():
                continue
            
            entry_text = entry_text.strip()
            if len(entry_text) > 5000:
                continue
            
            analysis_result = analyzer_instance.analyze_emotions_and_topics(entry_text)
            reflection = analyzer_instance.generate_reflection(entry_text, analysis_result)
            
            results.append({
                "analysis": analysis_result,
                "reflection": reflection
            })
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return jsonify({
            "results": results,
            "status": "success",
            "total_processed": len(results),
            "processing_time": round(processing_time, 2)
        })
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        return jsonify({"error": "Internal server error", "message": str(e), "status": "error"}), 500

# Vercel handler
app_handler = app

if __name__ == '__main__':
    app.run(debug=True, port=5050)
