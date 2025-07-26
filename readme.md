# 🧠 MindWeave Reflection Backend API

## 📊 Quick Reference

**Base URL:** `https://mind-be-ruddy.vercel.app`  
**API Version:** v0.2.0  
**Response Format:** JSON  
**Authentication:** None required  

---

## 🆕 What's New in v0.2.0

### 🎯 **MindWeave Features**
- **Emotion Quantification**: Precise numerical emotion analysis (values sum to 1.0)
- **Pattern Recognition**: Historical behavior insights with specific metrics
- **YSYM Analysis**: "You Said You Meant" - reveals hidden emotional truths
- **Smart Triggering**: YSYM only activates when negative emotions ≥ 60%

### 🔄 **3-Stage Gemini Processing**
1. **Emotion & Topic Analysis**: Quantified emotional breakdown + polarity
2. **MindWeave Reflection**: Pattern recognition with historical context
3. **YSYM Analysis**: Deep emotional insight (conditional)

---

## 🚀 Available Endpoints

### 1. Health Check
```http
GET /api/health
```
**Response Time:** ~100ms  

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-26T12:00:00",
  "service": "mindweave-reflection-backend",
  "version": "0.2.0",
  "environment": "vercel"
}
```

### 2. Test Endpoint
```http
GET /api/test
```
**Use Case:** Test all MindWeave features with sample data  
**Response Time:** ~5-8s (3 Gemini API calls)  

**Sample Response:**
```json
{
  "analysis": {
    "entry_text": "I stayed up until 3am working on my startup...",
    "emotions_quantified": {
      "overwhelmed": 0.4,
      "anxious": 0.35,
      "frustrated": 0.25
    },
    "emotion_polarity": {
      "positive": 0.0,
      "negative": 1.0
    },
    "topics": ["work", "health"],
    "timestamp": "2025-07-26T12:00:00"
  },
  "mindweave_reflection": "You've logged 11 late-night work sessions this month. Each time you mention being 'behind,' despite completing tasks. Your definition of 'caught up' appears to be a moving target.",
  "ysym": true,
  "ysym_analysis": "You said: I feel so behind → You meant: You're afraid your efforts will never be enough to meet your own impossible standards",
  "status": "success"
}
```

### 3. Analyze Entry ⭐ **MAIN ENDPOINT**
```http
POST /api/analyze
Content-Type: application/json
```

**Request Body:**
```json
{
  "entry_text": "Your journal entry text here (max 5000 chars)"
}
```

**Complete Response Structure:**
```json
{
  "analysis": {
    "entry_text": "Sarah didn't text me back for 3 hours, I shouldn't have sent that message",
    "emotions_quantified": {
      "anxious": 0.7,
      "regret": 0.2,
      "self_doubt": 0.1
    },
    "emotion_polarity": {
      "positive": 0.0,
      "negative": 1.0
    },
    "topics": ["relationships", "social"],
    "timestamp": "2025-07-26T12:00:00"
  },
  "mindweave_reflection": "This mirrors 4 similar entries about delayed responses triggering self-doubt. You consistently interpret silence as rejection within a 2-4 hour window. Your anxiety peaks before any actual negative outcome occurs.",
  "ysym": true,
  "ysym_analysis": "You said: Sarah didn't text back → You meant: You're afraid of being rejected or abandoned",
  "status": "success",
  "processing_time": 4.2
}
```

**When YSYM Doesn't Trigger (< 60% negative):**
```json
{
  "analysis": {
    "entry_text": "Had a great day! Finally finished that project",
    "emotions_quantified": {
      "happy": 0.5,
      "accomplished": 0.3,
      "proud": 0.2
    },
    "emotion_polarity": {
      "positive": 1.0,
      "negative": 0.0
    },
    "topics": ["work", "achievement"],
    "timestamp": "2025-07-26T12:00:00"
  },
  "mindweave_reflection": "First positive entry in 8 days. Completion of concrete tasks consistently correlates with improved mood in your history. Your wellbeing appears tied to tangible accomplishments rather than effort expended.",
  "ysym": false,
  "status": "success",
  "processing_time": 2.8
}
```

---

## 🎯 Feature Deep Dive

### **Emotion Quantification**
- **Format**: `{"emotion": decimal_value}`
- **Constraint**: All values sum to exactly 1.0
- **Use Case**: Perfect for pie charts and emotion visualization
- **Example**: `{"anxious": 0.6, "hopeful": 0.4}` = 60% anxious, 40% hopeful

### **MindWeave Reflections**
**Philosophy**: Pattern recognition engine that connects behaviors to emotional outcomes

**Characteristics**:
- Direct but not harsh tone
- Observational, not prescriptive  
- Mentions specific numbers and frequencies
- Reveals non-obvious behavioral patterns
- No advice, just awareness

**Example Patterns**:
- "You've cancelled plans 4 times this week"
- "11 late-night work sessions this month"
- "First positive entry in 8 days"

### **YSYM (You Said You Meant)**
**Purpose**: Reveals the gap between surface statements and deeper emotions

**Trigger Condition**: Negative emotions ≥ 60%  
**Format**: "You said: [surface] → You meant: [deeper truth]"

**Common Deep Patterns**:
- Control fears: "I forgot to..." → "Afraid of losing control"
- Abandonment fears: "They didn't respond" → "Afraid of rejection"
- Perfectionism: "I'm behind" → "Standards keep moving higher"

---

## 💻 Frontend Integration

### **React Hook Example**
```typescript
import { useState, useCallback } from 'react';

interface MindWeaveAnalysis {
  analysis: {
    entry_text: string;
    emotions_quantified: Record<string, number>;
    emotion_polarity: { positive: number; negative: number };
    topics: string[];
    timestamp: string;
  };
  mindweave_reflection: string;
  ysym: boolean;
  ysym_analysis?: string;
  status: string;
  processing_time: number;
}

export const useMindWeaveAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeEntry = useCallback(async (entryText: string): Promise<MindWeaveAnalysis | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('https://mind-be-ruddy.vercel.app/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_text: entryText })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Analysis failed');
      }
      
      const data = await response.json();
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { analyzeEntry, loading, error };
};
```

### **Emotion Pie Chart Integration**
```javascript
// Perfect for Chart.js or similar libraries
const createEmotionChart = (emotions_quantified) => {
  const labels = Object.keys(emotions_quantified);
  const data = Object.values(emotions_quantified);
  const percentages = data.map(value => (value * 100).toFixed(1));
  
  return {
    labels: labels,
    datasets: [{
      data: percentages,
      backgroundColor: [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
      ]
    }]
  };
};

// Usage
const result = await analyzeEntry("I feel anxious about tomorrow's presentation");
const chartData = createEmotionChart(result.analysis.emotions_quantified);
```

### **YSYM Conditional Rendering**
```jsx
const AnalysisResults = ({ result }) => {
  return (
    <div className="analysis-container">
      {/* Always show these */}
      <EmotionChart data={result.analysis.emotions_quantified} />
      <MindWeaveReflection text={result.mindweave_reflection} />
      
      {/* Conditionally show YSYM */}
      {result.ysym && (
        <div className="ysym-analysis">
          <h3>Deeper Insight</h3>
          <p>{result.ysym_analysis}</p>
        </div>
      )}
    </div>
  );
};
```

---

## 🔬 Testing & Development

### **Test Cases for Frontend**
```javascript
const testCases = [
  // Triggers YSYM (high negative emotions)
  {
    input: "I forgot to go to the gym again, I feel terrible about myself",
    expectYSYM: true,
    expectedNegative: "> 60%"
  },
  
  // Doesn't trigger YSYM (positive emotions)
  {
    input: "Had an amazing workout today, feeling energized and proud",
    expectYSYM: false,
    expectedNegative: "< 60%"
  },
  
  // Boundary case (around 60% negative)
  {
    input: "Work was stressful but I managed to finish the project",
    expectYSYM: "maybe", // depends on exact emotion analysis
    expectedNegative: "~60%"
  }
];
```

### **Error Handling**
```javascript
const handleAnalysisError = (error) => {
  if (error.message.includes('5000 characters')) {
    return "Entry too long. Please keep under 5000 characters.";
  }
  if (error.message.includes('rate limit')) {
    return "Too many requests. Please wait a moment and try again.";
  }
  return "Analysis temporarily unavailable. Please try again.";
};
```

---

## 📈 Performance & Best Practices

### **Response Times**
- **2 API calls** (no YSYM): ~2-3 seconds
- **3 API calls** (with YSYM): ~4-6 seconds
- **Health check**: ~100ms

### **Frontend Recommendations**
1. **Show Progressive Loading**: Display steps as they complete
2. **Implement Smart Retry**: Retry on 5xx errors, not 4xx
3. **Cache Wisely**: Don't cache failed analyses
4. **Validate Input**: Check length client-side before sending
5. **Handle YSYM**: Always check the `ysym` boolean flag

### **Rate Limiting**
- **Recommended**: Max 1 analysis per 3 seconds per user
- **Reason**: Each analysis uses 2-3 Gemini API calls
- **Implementation**: Debounce user input appropriately

---

## 🎯 Ready to Build Amazing Experiences!

**Key Integration Points:**
- ✅ Emotion quantification for beautiful visualizations
- ✅ Pattern recognition for meaningful insights  
- ✅ Conditional deep analysis for powerful moments
- ✅ Consistent API structure with clear error handling

**Contact:** gary@agryyang.in  
**Repository:** https://github.com/Gary0302/Mind_BE