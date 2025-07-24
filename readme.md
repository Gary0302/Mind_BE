# 🔗 Reflection Backend API - Frontend Integration Guide

## 📊 Quick Reference

**Base URL:** `https://mind-be-ruddy.vercel.app`  
**API Version:** v0.1.0  
**Response Format:** JSON  
**Authentication:** None required  

---

## 🚀 Available Endpoints

### 1. Health Check
```http
GET /api/health
```
**Use Case:** Check if API is running  
**Response Time:** ~100ms  

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-24T12:00:00",
  "service": "reflection-backend",
  "version": "0.1.0"
}
```

### 2. Test Endpoint
```http
GET /api/test
```
**Use Case:** Test API with sample data  
**Response Time:** ~3-5s  

**Response:**
```json
{
  "sample_analysis": {
    "entry_text": "Today I felt overwhelmed at work...",
    "emotions": ["overwhelmed", "proud", "accomplished"],
    "topics": ["work"],
    "timestamp": "2025-07-24T12:00:00"
  },
  "sample_reflection": "It's wonderful that you pushed through...",
  "status": "success",
  "message": "API is working correctly on Vercel"
}
```

### 3. Analyze Single Entry ⭐
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

**Response:**
```json
{
  "analysis": {
    "entry_text": "Your original text",
    "emotions": ["happy", "excited", "grateful"],
    "topics": ["family", "relationships"],
    "timestamp": "2025-07-24T12:00:00"
  },
  "reflection": "Generated empathetic reflection text...",
  "status": "success",
  "processing_time": 2.34
}
```

### 4. Batch Analyze ⭐
```http
POST /api/batch-analyze
Content-Type: application/json
```

**Request Body:**
```json
{
  "entries": [
    "First journal entry text",
    "Second journal entry text",
    "Third journal entry text"
  ]
}
```
**Limits:** Max 10 entries per request, 5000 chars per entry

**Response:**
```json
{
  "results": [
    {
      "analysis": {
        "entry_text": "First journal entry text",
        "emotions": ["happy", "content"],
        "topics": ["family"],
        "timestamp": "2025-07-24T12:00:00"
      },
      "reflection": "Generated reflection for first entry..."
    },
    {
      "analysis": {
        "entry_text": "Second journal entry text", 
        "emotions": ["motivated", "excited"],
        "topics": ["work", "goals"],
        "timestamp": "2025-07-24T12:00:01"
      },
      "reflection": "Generated reflection for second entry..."
    }
  ],
  "status": "success",
  "total_processed": 2,
  "processing_time": 5.67
}
```

---

## 💻 Frontend Integration Examples

### JavaScript/TypeScript

#### Basic Fetch
```javascript
// Single Analysis
async function analyzeEntry(entryText) {
  try {
    const response = await fetch('https://mind-9nhqoiay9-garys-projects-14822d8b.vercel.app/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        entry_text: entryText
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
}

// Usage
const result = await analyzeEntry("Today I felt happy and accomplished!");
console.log(result.analysis.emotions); // ["happy", "accomplished"]
console.log(result.reflection); // Generated reflection text
```

#### Axios
```javascript
import axios from 'axios';

const API_BASE_URL = 'https://mind-9nhqoiay9-garys-projects-14822d8b.vercel.app';

// Single Analysis
export const analyzeEntry = async (entryText) => {
  const response = await axios.post(`${API_BASE_URL}/api/analyze`, {
    entry_text: entryText
  });
  return response.data;
};

// Batch Analysis
export const batchAnalyze = async (entries) => {
  const response = await axios.post(`${API_BASE_URL}/api/batch-analyze`, {
    entries: entries
  });
  return response.data;
};

// Health Check
export const checkHealth = async () => {
  const response = await axios.get(`${API_BASE_URL}/api/health`);
  return response.data;
};
```

### React Hook Example
```typescript
import { useState, useCallback } from 'react';

interface AnalysisResult {
  analysis: {
    entry_text: string;
    emotions: string[];
    topics: string[];
    timestamp: string;
  };
  reflection: string;
  status: string;
  processing_time: number;
}

export const useReflectionAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeEntry = useCallback(async (entryText: string): Promise<AnalysisResult | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('https://mind-9nhqoiay9-garys-projects-14822d8b.vercel.app/api/analyze', {
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

### Vue.js Composable
```typescript
import { ref, reactive } from 'vue';

export function useReflectionAPI() {
  const loading = ref(false);
  const error = ref<string | null>(null);
  
  const analyzeEntry = async (entryText: string) => {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await fetch('https://mind-9nhqoiay9-garys-projects-14822d8b.vercel.app/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_text: entryText })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error);
      }
      
      return await response.json();
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };
  
  return { analyzeEntry, loading: readonly(loading), error: readonly(error) };
}
```

---

## ⚠️ Error Handling

### Common Error Responses

#### 400 - Bad Request
```json
{
  "error": "entry_text field is required",
  "status": "error"
}
```

#### 500 - Server Error
```json
{
  "error": "Internal server error",
  "message": "Detailed error message",
  "status": "error"
}
```

### Frontend Error Handling
```javascript
try {
  const result = await analyzeEntry(text);
  // Handle success
} catch (error) {
  if (error.response?.status === 400) {
    // Handle validation errors
    alert('Please check your input');
  } else if (error.response?.status === 500) {
    // Handle server errors
    alert('Server error, please try again later');
  } else {
    // Handle network errors
    alert('Network error, check your connection');
  }
}
```

---

## 📊 Data Reference

### Possible Emotions
```javascript
const EMOTIONS = [
  'happy', 'sad', 'anxious', 'calm', 'excited', 'proud', 
  'frustrated', 'overwhelmed', 'grateful', 'content', 
  'stressed', 'relaxed', 'worried', 'confident', 'confused',
  'angry', 'peaceful', 'hopeful', 'disappointed', 'motivated',
  'tired', 'energetic', 'lonely', 'loved', 'fearful',
  'optimistic', 'pessimistic', 'curious', 'satisfied', 'nervous'
];
```

### Possible Topics
```javascript
const TOPICS = [
  'family', 'work', 'exercise', 'relationships', 'health',
  'travel', 'social', 'personal_growth', 'education', 'finances',
  'hobbies', 'spiritual', 'career', 'creativity', 'nature',
  'technology', 'food', 'entertainment', 'home', 'friends',
  'goals', 'challenges'
];
```

---

## ⚡ Performance & Best Practices

### Response Times
- **Cold Start:** 3-5 seconds (first request after idle)
- **Hot Requests:** 1-3 seconds (subsequent requests)
- **Batch Processing:** 2-10 seconds (depending on entry count)

### Optimization Tips
1. **Show Loading States:** Always show loading indicators for 2-5 second delays
2. **Implement Retry Logic:** Handle temporary failures gracefully
3. **Cache Results:** Consider caching analysis results to avoid re-processing
4. **Debounce Input:** For real-time analysis, debounce user input
5. **Batch When Possible:** Use batch endpoint for multiple entries

### Rate Limiting
- No explicit rate limits currently
- Recommended: Max 1 request per second per user
- Use request queuing for multiple rapid requests

---

## 🧪 Testing

### Test Data
```javascript
// Test cases for your frontend
const testCases = [
  {
    input: "Today I felt overwhelmed at work but completed my project.",
    expectedEmotions: ["overwhelmed", "accomplished", "proud"],
    expectedTopics: ["work"]
  },
  {
    input: "Had a wonderful time with family at dinner.",
    expectedEmotions: ["happy", "grateful", "content"],
    expectedTopics: ["family", "social"]
  },
  {
    input: "Yoga session helped me feel centered and peaceful.",
    expectedEmotions: ["calm", "peaceful", "centered"],
    expectedTopics: ["exercise", "health"]
  }
];
```

### Health Check Integration
```javascript
// Add to your app's health check
const checkAPIHealth = async () => {
  try {
    const response = await fetch('https://mind-9nhqoiay9-garys-projects-14822d8b.vercel.app/api/health');
    const data = await response.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
};
```

---

## 🚀 Ready to Integrate!

**Next Steps:**
1. Test the API endpoints using the examples above
2. Implement error handling for your use cases
3. Add loading states for better UX
4. Consider caching strategies for frequently accessed data

**Need Help?** 
- Test all endpoints work: ✅
- Response format is consistent: ✅  
- Error handling is clear: ✅
- Performance is acceptable: ✅

**Contact:** gary@agryyang.in