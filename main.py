from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import json
import logging
from datetime import datetime
import re
from typing import Dict, List, Optional, Any

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
    
    def analyze_emotions_and_topics(self, entry_text: str) -> Dict[str, Any]:
        """
        First Gemini API call: Analyze emotions, topics, and quantify emotions
        """
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
        - Return 2-4 emotions with their intensity values
        - Return 1-3 topics that best categorize the content
        - Ensure all emotion values are between 0.0 and 1.0 and sum exactly to 1.0
        - Only return valid JSON, no additional text or formatting
        
        Example:
        {{"emotions_quantified": {{"anxious": 0.6, "hopeful": 0.4}}, "emotion_polarity": {{"positive": 0.4, "negative": 0.6}}, "topics": ["work", "personal_growth"]}}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            
            result_text = response.text.strip()
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            parsed_result = json.loads(result_text)
            
            # Validate the response
            emotions_quantified = parsed_result.get('emotions_quantified', {})
            emotion_polarity = parsed_result.get('emotion_polarity', {'positive': 0.5, 'negative': 0.5})
            topics = parsed_result.get('topics', ['general'])
            
            # Ensure emotions sum to 1.0 (normalize if needed)
            emotion_sum = sum(emotions_quantified.values())
            if emotion_sum > 0:
                emotions_quantified = {k: round(v / emotion_sum, 3) for k, v in emotions_quantified.items()}
            
            # Ensure polarity sums to 1.0
            polarity_sum = sum(emotion_polarity.values())
            if polarity_sum > 0:
                emotion_polarity = {k: round(v / polarity_sum, 3) for k, v in emotion_polarity.items()}
            
            return {
                'entry_text': entry_text,
                'emotions_quantified': emotions_quantified,
                'emotion_polarity': emotion_polarity,
                'topics': topics[:3],
                'timestamp': datetime.now().isoformat()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in analysis: {str(e)}")
            return self._fallback_analysis(entry_text)
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            return self._fallback_analysis(entry_text)
    
    def generate_mindweave_reflection(self, entry_text: str, analysis_result: Dict[str, Any]) -> str:
        """
        Second Gemini API call: Generate MindWeave pattern recognition reflection
        """
        emotions_str = ", ".join([f"{emotion}: {value}" for emotion, value in analysis_result.get('emotions_quantified', {}).items()])
        topics_str = ", ".join(analysis_result.get('topics', []))
        
        prompt = f"""
        You are a pattern recognition engine for MindWeave Reflections. Your job is to identify behavioral and emotional patterns, not give advice.

        **Core Philosophy:** Connect repeated behaviors to emotional outcomes. Make invisible patterns obvious. Reveal what supports or sabotages wellbeing.

        **Entry to analyze:** "{entry_text}"
        **Detected emotions:** {emotions_str}
        **Topics:** {topics_str}

        **Tone Guidelines:**
        - Direct but not harsh
        - Observational, not prescriptive
        - State patterns, don't give advice
        - Mention recurring outcomes
        - Precise language - no fluff

        **Structure Formula:**
        1. Mirror statement (what happened)
        2. Pattern recognition (historical connection - simulate past entries)
        3. System insight (what this reveals about behavior/thinking)

        **Example format:**
        "You [action/feeling] → [X] similar entries show [pattern] → You tend to [behavioral insight]."

        **Sample outputs for reference:**
        - "This mirrors 4 similar entries about delayed responses triggering self-doubt. You consistently interpret silence as rejection within a 2-4 hour window."
        - "You've logged 11 late-night work sessions this month. Each time you mention being 'behind,' despite completing tasks."
        - "First positive entry in 8 days. Completion of concrete tasks consistently correlates with improved mood in your history."

        **Requirements:**
        - Use specific numbers (simulate realistic historical data)
        - Identify non-obvious connections
        - State facts, not opinions
        - No advice or judgment
        - 2-3 sentences maximum
        - Focus on actionable awareness

        Generate a MindWeave reflection based on the entry and emotional analysis above:
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
            logger.error(f"Error in MindWeave reflection generation: {str(e)}")
            return "Pattern analysis temporarily unavailable. Your entry has been recorded for future insights."
    
    def generate_ysym_analysis(self, entry_text: str, analysis_result: Dict[str, Any]) -> str:
        """
        Third Gemini API call: Generate "You Said You Meant" analysis
        Only called when negative emotions >= 60%
        """
        emotions_str = ", ".join([f"{emotion}: {value}" for emotion, value in analysis_result.get('emotions_quantified', {}).items()])
        negative_percentage = analysis_result.get('emotion_polarity', {}).get('negative', 0) * 100
        
        prompt = f"""
        You are analyzing the gap between surface statements and underlying emotions for "You Said You Meant" feature.

        **Entry:** "{entry_text}"
        **Emotions detected:** {emotions_str}
        **Negative emotion level:** {negative_percentage:.1f}%

        Your task is to identify:
        - **Surface statement:** What the person explicitly said/described
        - **Underlying meaning:** The deeper emotional truth or fear behind it

        **Guidelines:**
        - Focus on the emotional subtext, not the literal content
        - Identify core fears: abandonment, failure, rejection, judgment, loss of control
        - Be direct but compassionate
        - No advice, just observation
        - Format: "You said: [surface] → You meant: [deeper truth]"

        **Examples:**
        - Entry: "I forgot to go to the gym, I feel really bad"
          → "You said: I forgot to go to the gym → You meant: You're afraid of losing control over your progress"

        - Entry: "Sarah didn't text me back for 3 hours"
          → "You said: Sarah didn't text back → You meant: You're afraid of being abandoned or rejected"

        **Requirements:**
        - Keep it concise (1-2 sentences)
        - Focus on emotional truth, not behavioral advice
        - Identify the core fear or need beneath the surface

        Generate the You Said You Meant analysis:
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error in YSYM analysis generation: {str(e)}")
            return "You said: [Current entry] → You meant: [Deeper insight temporarily unavailable]"
    
    def _fallback_analysis(self, entry_text: str) -> Dict[str, Any]:
        """Fallback analysis when primary analysis fails"""
        return {
            'entry_text': entry_text,
            'emotions_quantified': {'neutral': 1.0},
            'emotion_polarity': {'positive': 0.5, 'negative': 0.5},
            'topics': ['general'],
            'timestamp': datetime.now().isoformat(),
            'fallback_used': True
        }

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
        "message": "MindWeave Reflection Backend API",
        "version": "0.2.0",
        "status": "running",
        "environment": "vercel",
        "features": [
            "Emotion quantification",
            "MindWeave pattern recognition",
            "You Said You Meant analysis",
            "Conditional YSYM triggering (60% negative threshold)"
        ],
        "endpoints": {
            "health": "/api/health",
            "test": "/api/test",
            "analyze": "/api/analyze (POST)"
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mindweave-reflection-backend",
        "version": "0.2.0",
        "environment": "vercel"
    })

@app.route('/api/test')
def test_endpoint():
    sample_entry = "I stayed up until 3am working on my startup again. I know I shouldn't but I feel so behind on everything. Sarah didn't reply to my message either, which makes me think she's avoiding me."
    
    try:
        analyzer_instance = get_analyzer()
        
        # First API call: Emotion and topic analysis
        analysis_result = analyzer_instance.analyze_emotions_and_topics(sample_entry)
        
        # Second API call: MindWeave reflection
        mindweave_reflection = analyzer_instance.generate_mindweave_reflection(sample_entry, analysis_result)
        
        # Check if YSYM should be triggered (negative emotions >= 60%)
        negative_ratio = analysis_result.get('emotion_polarity', {}).get('negative', 0)
        ysym_triggered = negative_ratio >= 0.6
        
        response_data = {
            "analysis": analysis_result,
            "mindweave_reflection": mindweave_reflection,
            "ysym": ysym_triggered,
            "status": "success",
            "message": "API test successful with MindWeave features"
        }
        
        # Third API call: YSYM analysis (conditional)
        if ysym_triggered:
            ysym_analysis = analyzer_instance.generate_ysym_analysis(sample_entry, analysis_result)
            response_data["ysym_analysis"] = ysym_analysis
        
        return jsonify(response_data)
        
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
        
        # First Gemini API call: Emotion and topic analysis with quantification
        logger.info("Starting first Gemini API call: emotion analysis")
        analysis_result = analyzer_instance.analyze_emotions_and_topics(entry_text)
        
        # Second Gemini API call: MindWeave reflection
        logger.info("Starting second Gemini API call: MindWeave reflection")
        mindweave_reflection = analyzer_instance.generate_mindweave_reflection(entry_text, analysis_result)
        
        # Check if YSYM should be triggered (negative emotions >= 60%)
        negative_ratio = analysis_result.get('emotion_polarity', {}).get('negative', 0)
        ysym_triggered = negative_ratio >= 0.6
        
        logger.info(f"Negative emotion ratio: {negative_ratio:.2f}, YSYM triggered: {ysym_triggered}")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        response_data = {
            "analysis": analysis_result,
            "mindweave_reflection": mindweave_reflection,
            "ysym": ysym_triggered,
            "status": "success",
            "processing_time": round(processing_time, 2)
        }
        
        # Third Gemini API call: YSYM analysis (conditional)
        if ysym_triggered:
            logger.info("Starting third Gemini API call: YSYM analysis")
            ysym_analysis = analyzer_instance.generate_ysym_analysis(entry_text, analysis_result)
            response_data["ysym_analysis"] = ysym_analysis
            
            # Update processing time after YSYM
            final_time = datetime.now()
            response_data["processing_time"] = round((final_time - start_time).total_seconds(), 2)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing entry: {str(e)}")
        return jsonify({"error": "Internal server error", "message": str(e), "status": "error"}), 500

@app.route('/api/batch-analyze', methods=['POST'])
def batch_analyze():
    return jsonify({"error": "Batch analysis temporarily disabled during MindWeave implementation"}), 503

# Vercel handler
app_handler = app

if __name__ == '__main__':
    app.run(debug=True, port=5050)