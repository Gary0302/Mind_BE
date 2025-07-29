# 🧠 MindWeave Backend API - Developer Guide

*[中文版本請見下方 | Traditional Chinese version below](#中文開發者指南)*

## 📋 API Reference for Frontend Developers

**Production Base URL:** `https://mind-be-ruddy.vercel.app`  
**API Version:** v0.2.0  
**Content-Type:** `application/json`  
**Authentication:** JWT Bearer tokens

---

## 🚀 Quick Start

### Step 1: Test Basic Connectivity
```bash
curl https://mind-be-ruddy.vercel.app/api/health
```

### Step 2: Try Guest Mode Analysis
```bash
curl -X POST https://mind-be-ruddy.vercel.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"entry_text": "I feel great today and excited about my new project!"}'
```

### Step 3: Register a User and Get Tokens
```bash
curl -X POST https://mind-be-ruddy.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "username": "developer"}'
```

---

## 🔐 Authentication Flow

### 1. User Registration
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",     // optional
  "username": "username123"        // optional (at least one required)
}
```

**Response:**
```json
{
  "user": {
    "user_id": "ce56ee93-eb02-49ec-b68e-9a8e266688d3",
    "email": "user@example.com",
    "username": "username123",
    "display_name": "username123",
    "plan_type": "free",
    "created_at": "2025-07-29T05:50:02.899781+00:00"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "f4ca06ad-dacf-4956-9f4a-b431e9e9073b"
  },
  "message": "User created successfully"
}
```

### 2. User Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:** Same format as registration

### 3. Using JWT Tokens
Include the access token in all authenticated requests:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🧠 Analysis API

### Guest Mode (No Authentication)
```http
POST /api/analyze
Content-Type: application/json

{
  "entry_text": "Your journal entry text here (max 5000 chars)"
}
```

**Example Response:**
```json
{
  "analysis": {
    "emotions_quantified": {
      "joy": 0.6,
      "excitement": 0.4
    },
    "emotion_polarity": {
      "positive": 1.0,
      "negative": 0.0
    },
    "topics": ["personal_growth", "work"],
    "timestamp": "2025-07-29T05:32:43.148487"
  },
  "mindweave_reflection": "This entry beautifully captures a sense of joy and excitement about new opportunities.",
  "ysym": false,
  "mode": "guest",
  "stored": false,
  "processing_time": 1.52,
  "message": "Register to unlock historical insights!",
  "benefits": [
    "Track emotional patterns over time",
    "Get insights based on your history",
    "Search through past entries"
  ]
}
```

### User Mode (With Authentication & Historical Context)
```http
POST /api/analyze
Content-Type: application/json
Authorization: Bearer your_access_token

{
  "entry_text": "I'm feeling overwhelmed with work again, just like last week.",
  "user_id": "ce56ee93-eb02-49ec-b68e-9a8e266688d3"
}
```

**Example Response:**
```json
{
  "analysis": {
    "emotions_quantified": {
      "overwhelmed": 0.5,
      "stressed": 0.3,
      "anxious": 0.2
    },
    "emotion_polarity": {
      "positive": 0.0,
      "negative": 1.0
    },
    "topics": ["work", "personal_wellbeing"]
  },
  "mindweave_reflection": "This is your 3rd entry about work overwhelm this month. Pattern shows stress typically peaks mid-week, with 85% of similar entries followed by weekend recovery.",
  "ysym": true,
  "ysym_analysis": "You said: feeling overwhelmed with work → You meant: I'm afraid I can't meet expectations and might be failing",
  "mode": "user",
  "stored": true,
  "historical_entries_used": 12,
  "processing_time": 4.2
}
```

### YSYM Triggering Logic
- **Triggered when:** `emotion_polarity.negative >= 0.6` (60% or more negative emotions)
- **Response includes:** `ysym_analysis` field with deeper emotional insights

---

## 🔍 Search API

### Search User's Entries
```http
POST /api/search
Content-Type: application/json
Authorization: Bearer your_access_token

{
  "search_query": "anxious",           // optional - keyword search
  "start_date": "2025-07-01",         // optional - YYYY-MM-DD format
  "end_date": "2025-07-29",           // optional - YYYY-MM-DD format
  "limit": 20                          // optional - max 100, default 50
}
```

**Example Response:**
```json
{
  "results": [
    {
      "entry_id": "cea0d58a-1b94-4c3b-92ff-935d11e70e19",
      "entry_text": "I feel anxious about my presentation tomorrow...",
      "created_at": "2025-07-29T05:51:33.479217+00:00",
      "emotions_quantified": {
        "anxious": 0.8,
        "stressed": 0.2
      },
      "topics": ["work", "social"],
      "relevance_score": 0.0607927
    }
  ],
  "count": 1,
  "search_params": {
    "query": "anxious",
    "start_date": null,
    "end_date": null,
    "limit": 50
  }
}
```

---

## 👤 User Management API

### Get User Profile
```http
GET /api/user/profile
Authorization: Bearer your_access_token
```

**Response:**
```json
{
  "user": {
    "user_id": "ce56ee93-eb02-49ec-b68e-9a8e266688d3",
    "email": "user@example.com",
    "username": "username123",
    "plan_type": "free",
    "created_at": "2025-07-29T05:50:02.899781+00:00"
  },
  "stats": {
    "total_entries_30_days": 15,
    "top_emotions": {
      "happy": 2.4,
      "anxious": 1.8,
      "excited": 1.2
    },
    "top_topics": ["work", "personal_growth", "relationships"]
  }
}
```

### Import Guest Data
```http
POST /api/user/import-guest-data
Content-Type: application/json
Authorization: Bearer your_access_token

{
  "analyses": [
    {
      "entry_text": "Previous guest analysis text",
      "analysis": {
        "emotions_quantified": {"happy": 0.8, "excited": 0.2},
        "emotion_polarity": {"positive": 1.0, "negative": 0.0},
        "topics": ["personal_growth"]
      },
      "mindweave_reflection": "Guest mode reflection text",
      "ysym_analysis": null
    }
  ]
}
```

**Response:**
```json
{
  "imported": 1,
  "failed": 0,
  "total_provided": 1,
  "status": "success"
}
```

---

## 🛠️ Utility Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T05:32:33.850941",
  "service": "mindweave-reflection-backend",
  "version": "0.2.0",
  "environment": "vercel",
  "integrations": {
    "gemini": "connected",
    "supabase": "connected"
  }
}
```

### Test Endpoint (Sample Analysis)
```http
GET /api/test
```

Returns a complete analysis example with sample data.

### API Information
```http
GET /
```

Returns API documentation and endpoint list.

---

## 💻 Frontend Integration Examples

### React TypeScript Hook
```typescript
import { useState, useCallback } from 'react';

interface MindWeaveAPI {
  baseUrl: string;
  authToken?: string;
}

interface AnalysisRequest {
  entry_text: string;
  user_id?: string;
}

interface AnalysisResponse {
  analysis: {
    emotions_quantified: Record<string, number>;
    emotion_polarity: { positive: number; negative: number };
    topics: string[];
    timestamp: string;
  };
  mindweave_reflection: string;
  ysym: boolean;
  ysym_analysis?: string;
  mode: 'guest' | 'user';
  stored: boolean;
  processing_time: number;
}

export const useMindWeaveAPI = ({ baseUrl, authToken }: MindWeaveAPI) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiCall = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }

    return data;
  }, [baseUrl, authToken]);

  const analyzeEntry = useCallback(async (request: AnalysisRequest): Promise<AnalysisResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const data = await apiCall('/api/analyze', {
        method: 'POST',
        body: JSON.stringify(request),
      });
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const searchEntries = useCallback(async (params: {
    search_query?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }) => {
    setLoading(true);
    setError(null);

    try {
      const data = await apiCall('/api/search', {
        method: 'POST',
        body: JSON.stringify(params),
      });
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const registerUser = useCallback(async (credentials: {
    email?: string;
    username?: string;
  }) => {
    setLoading(true);
    setError(null);

    try {
      const data = await apiCall('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  return {
    analyzeEntry,
    searchEntries,
    registerUser,
    loading,
    error,
  };
};
```

### React Component Example
```typescript
import React, { useState } from 'react';
import { useMindWeaveAPI } from './hooks/useMindWeaveAPI';

const MindWeaveAnalyzer: React.FC = () => {
  const [entryText, setEntryText] = useState('');
  const [result, setResult] = useState<any>(null);
  
  const { analyzeEntry, loading, error } = useMindWeaveAPI({
    baseUrl: 'https://mind-be-ruddy.vercel.app',
    // authToken: localStorage.getItem('mindweave_token') // if user is logged in
  });

  const handleAnalyze = async () => {
    if (!entryText.trim()) return;
    
    const result = await analyzeEntry({ entry_text: entryText });
    if (result) {
      setResult(result);
    }
  };

  return (
    <div className="mindweave-analyzer">
      <textarea
        value={entryText}
        onChange={(e) => setEntryText(e.target.value)}
        placeholder="How are you feeling today?"
        maxLength={5000}
        rows={4}
        className="w-full p-3 border rounded"
      />
      
      <button
        onClick={handleAnalyze}
        disabled={loading || !entryText.trim()}
        className="mt-2 px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
      >
        {loading ? 'Analyzing...' : 'Analyze Entry'}
      </button>

      {error && (
        <div className="mt-2 p-2 bg-red-100 text-red-700 rounded">
          Error: {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="p-3 bg-blue-50 rounded">
            <h3 className="font-bold">Emotions:</h3>
            {Object.entries(result.analysis.emotions_quantified).map(([emotion, value]) => (
              <div key={emotion} className="flex justify-between">
                <span>{emotion}:</span>
                <span>{Math.round(value * 100)}%</span>
              </div>
            ))}
          </div>

          <div className="p-3 bg-green-50 rounded">
            <h3 className="font-bold">MindWeave Insight:</h3>
            <p>{result.mindweave_reflection}</p>
          </div>

          {result.ysym && (
            <div className="p-3 bg-purple-50 rounded">
              <h3 className="font-bold">Deeper Analysis (YSYM):</h3>
              <p>{result.ysym_analysis}</p>
            </div>
          )}

          <div className="text-sm text-gray-500">
            Mode: {result.mode} | Processing time: {result.processing_time}s
          </div>
        </div>
      )}
    </div>
  );
};

export default MindWeaveAnalyzer;
```

---

## ⚡ Performance & Best Practices

### Response Times
- **Guest mode**: 1.5-3 seconds
- **User mode**: 3-5 seconds (includes historical analysis)
- **Search**: 200-500ms
- **Authentication**: 100-300ms

### Rate Limiting Guidelines
- Implement 3-second debounce on analysis requests
- Cache user profile data locally
- Show loading states for better UX

### Error Handling
```typescript
const handleError = (error: string) => {
  if (error.includes('5000 characters')) {
    return 'Entry too long. Please keep under 5000 characters.';
  }
  if (error.includes('token')) {
    return 'Please log in again.';
  }
  if (error.includes('rate limit')) {
    return 'Too many requests. Please wait a moment.';
  }
  return 'Something went wrong. Please try again.';
};
```

---

## 🧪 Complete Testing Examples

### Test Suite for Frontend Developers
```javascript
// Test basic connectivity
const testHealth = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/health');
  console.log('Health:', await response.json());
};

// Test guest mode analysis
const testGuestAnalysis = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entry_text: "I'm feeling excited about this new project but also a bit nervous about the challenges ahead."
    })
  });
  console.log('Guest Analysis:', await response.json());
};

// Test user registration
const testRegistration = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'test-' + Date.now() + '@example.com',
      username: 'testuser' + Date.now()
    })
  });
  const result = await response.json();
  console.log('Registration:', result);
  return result.tokens?.access_token;
};

// Test user mode analysis
const testUserAnalysis = async (token: string, userId: string) => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      entry_text: "Today was stressful at work, similar to how I felt last week when dealing with the deadline pressure.",
      user_id: userId
    })
  });
  console.log('User Analysis:', await response.json());
};

// Test search functionality
const testSearch = async (token: string) => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      search_query: 'stress',
      limit: 10
    })
  });
  console.log('Search Results:', await response.json());
};

// Run complete test suite
const runTests = async () => {
  console.log('🧪 Starting MindWeave API Tests...\n');
  
  // Test 1: Health check
  await testHealth();
  
  // Test 2: Guest analysis
  await testGuestAnalysis();
  
  // Test 3: User registration and get token
  const token = await testRegistration();
  
  if (token) {
    // Test 4: User analysis with token
    // Note: Extract user_id from the registration response
    await testUserAnalysis(token, 'user-id-from-registration');
    
    // Test 5: Search
    await testSearch(token);
  }
  
  console.log('\n✅ All tests completed!');
};

// runTests();
```

---

## ❌ Error Responses

### Common Error Formats
```json
// 400 Bad Request
{
  "error": "entry_text field is required",
  "status": "error"
}

// 401 Unauthorized
{
  "error": "Invalid token",
  "status": "error"
}

// 500 Internal Server Error
{
  "error": "Internal server error",
  "message": "Analysis temporarily unavailable",
  "status": "error"
}
```

### Error Handling in Frontend
```typescript
const handleApiError = (error: any) => {
  if (error.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.status === 400) {
    // Show validation error
    setErrorMessage(error.error);
  } else {
    // Show generic error
    setErrorMessage('Something went wrong. Please try again.');
  }
};
```

---

# 中文開發者指南

## 📋 前端開發者 API 參考

**生產環境基礎網址:** `https://mind-be-ruddy.vercel.app`  
**API 版本:** v0.2.0  
**內容類型:** `application/json`  
**身份驗證:** JWT Bearer 令牌

---

## 🚀 快速開始

### 步驟 1: 測試基本連接
```bash
curl https://mind-be-ruddy.vercel.app/api/health
```

### 步驟 2: 嘗試訪客模式分析
```bash
curl -X POST https://mind-be-ruddy.vercel.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"entry_text": "我今天感覺很棒，對我的新專案很興奮！"}'
```

### 步驟 3: 註冊用戶並獲取令牌
```bash
curl -X POST https://mind-be-ruddy.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "username": "developer"}'
```

---

## 🔐 身份驗證流程

### 1. 用戶註冊
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",     // 可選
  "username": "username123"        // 可選（至少一個必填）
}
```

**回應範例:**
```json
{
  "user": {
    "user_id": "ce56ee93-eb02-49ec-b68e-9a8e266688d3",
    "email": "user@example.com",
    "username": "username123",
    "display_name": "username123",
    "plan_type": "free",
    "created_at": "2025-07-29T05:50:02.899781+00:00"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "f4ca06ad-dacf-4956-9f4a-b431e9e9073b"
  },
  "message": "User created successfully"
}
```

### 2. 用戶登入
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**回應:** 與註冊相同格式

### 3. 使用 JWT 令牌
在所有需要驗證的請求中包含訪問令牌：
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🧠 分析 API

### 訪客模式（無需驗證）
```http
POST /api/analyze
Content-Type: application/json

{
  "entry_text": "你的日記條目文字（最多 5000 字元）"
}
```

**回應範例:**
```json
{
  "analysis": {
    "emotions_quantified": {
      "joy": 0.6,
      "excitement": 0.4
    },
    "emotion_polarity": {
      "positive": 1.0,
      "negative": 0.0
    },
    "topics": ["personal_growth", "work"],
    "timestamp": "2025-07-29T05:32:43.148487"
  },
  "mindweave_reflection": "這個條目美好地捕捉了對新機會的喜悅和興奮。",
  "ysym": false,
  "mode": "guest",
  "stored": false,
  "processing_time": 1.52,
  "message": "註冊以解鎖歷史洞察功能！",
  "benefits": [
    "追蹤情緒模式變化",
    "基於歷史的洞察分析",
    "搜尋過往條目"
  ]
}
```

### 用戶模式（含驗證和歷史脈絡）
```http
POST /api/analyze
Content-Type: application/json
Authorization: Bearer your_access_token

{
  "entry_text": "我又感到工作壓力很大，就像上週一樣。",
  "user_id": "ce56ee93-eb02-49ec-b68e-9a8e266688d3"
}
```

**回應範例:**
```json
{
  "analysis": {
    "emotions_quantified": {
      "overwhelmed": 0.5,
      "stressed": 0.3,
      "anxious": 0.2
    },
    "emotion_polarity": {
      "positive": 0.0,
      "negative": 1.0
    },
    "topics": ["work", "personal_wellbeing"]
  },
  "mindweave_reflection": "這是你本月第3次關於工作壓力的條目。模式顯示壓力通常在週中達到高峰，85%的類似條目之後都有週末恢復。",
  "ysym": true,
  "ysym_analysis": "你說：感到工作壓力很大 → 你想表達：我害怕無法達到期望，可能會失敗",
  "mode": "user",
  "stored": true,
  "historical_entries_used": 12,
  "processing_time": 4.2
}
```

---

## 🔍 搜尋 API

### 搜尋用戶條目
```http
POST /api/search
Content-Type: application/json
Authorization: Bearer your_access_token

{
  "search_query": "焦慮",               // 可選 - 關鍵字搜尋
  "start_date": "2025-07-01",         // 可選 - YYYY-MM-DD 格式
  "end_date": "2025-07-29",           // 可選 - YYYY-MM-DD 格式
  "limit": 20                          // 可選 - 最大 100，預設 50
}
```

**回應範例:**
```json
{
  "results": [
    {
      "entry_id": "cea0d58a-1b94-4c3b-92ff-935d11e70e19",
      "entry_text": "我對明天的演講感到焦慮...",
      "created_at": "2025-07-29T05:51:33.479217+00:00",
      "emotions_quantified": {
        "anxious": 0.8,
        "stressed": 0.2
      },
      "topics": ["work", "social"],
      "relevance_score": 0.0607927
    }
  ],
  "count": 1,
  "search_params": {
    "query": "焦慮",
    "start_date": null,
    "end_date": null,
    "limit": 50
  }
}
```

---

## 💻 React 整合範例

### React TypeScript Hook
```typescript
import { useState, useCallback } from 'react';

interface MindWeaveAPI {
  baseUrl: string;
  authToken?: string;
}

interface AnalysisRequest {
  entry_text: string;
  user_id?: string;
}

export const useMindWeaveAPI = ({ baseUrl, authToken }: MindWeaveAPI) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeEntry = useCallback(async (request: AnalysisRequest) => {
    setLoading(true);
    setError(null);

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${baseUrl}/api/analyze`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || '分析失敗');
      }

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知錯誤';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [baseUrl, authToken]);

  return { analyzeEntry, loading, error };
};
```

---

## 🧪 完整測試範例

### 前端開發者測試套件
```javascript
// 測試基本連接
const testHealth = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/health');
  console.log('健康檢查:', await response.json());
};

// 測試訪客模式分析
const testGuestAnalysis = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entry_text: "我對這個新專案感到興奮，但也對即將面臨的挑戰有點緊張。"
    })
  });
  console.log('訪客模式分析:', await response.json());
};

// 測試用戶註冊
const testRegistration = async () => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'test-' + Date.now() + '@example.com',
      username: 'testuser' + Date.now()
    })
  });
  const result = await response.json();
  console.log('用戶註冊:', result);
  return result.tokens?.access_token;
};

// 測試用戶模式分析
const testUserAnalysis = async (token: string, userId: string) => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      entry_text: "今天工作很有壓力，類似於上週處理截止日期壓力時的感受。",
      user_id: userId
    })
  });
  console.log('用戶模式分析:', await response.json());
};

// 測試搜尋功能
const testSearch = async (token: string) => {
  const response = await fetch('https://mind-be-ruddy.vercel.app/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      search_query: '壓力',
      limit: 10
    })
  });
  console.log('搜尋結果:', await response.json());
};

// 執行完整測試套件
const runTests = async () => {
  console.log('🧪 開始 MindWeave API 測試...\n');
  
  // 測試 1: 健康檢查
  await testHealth();
  
  // 測試 2: 訪客分析
  await testGuestAnalysis();
  
  // 測試 3: 用戶註冊並獲取令牌
  const token = await testRegistration();
  
  if (token) {
    // 測試 4: 使用令牌進行用戶分析
    // 注意：從註冊回應中提取 user_id
    await testUserAnalysis(token, 'user-id-from-registration');
    
    // 測試 5: 搜尋
    await testSearch(token);
  }
  
  console.log('\n✅ 所有測試完成！');
};

// runTests();
```

---

## ❌ 錯誤回應

### 常見錯誤格式
```json
// 400 錯誤請求
{
  "error": "entry_text field is required",
  "status": "error"
}

// 401 未授權
{
  "error": "Invalid token",
  "status": "error"
}

// 500 內部伺服器錯誤
{
  "error": "Internal server error",
  "message": "Analysis temporarily unavailable",
  "status": "error"
}
```

### 前端錯誤處理
```typescript
const handleApiError = (error: any) => {
  if (error.status === 401) {
    // 重定向到登入頁面
    window.location.href = '/login';
  } else if (error.status === 400) {
    // 顯示驗證錯誤
    setErrorMessage(error.error);
  } else {
    // 顯示通用錯誤
    setErrorMessage('發生錯誤，請稍後再試。');
  }
};
```

---

## ⚡ 效能與最佳實踐

### 回應時間
- **訪客模式**: 1.5-3 秒
- **用戶模式**: 3-5 秒（包含歷史分析）
- **搜尋**: 200-500 毫秒
- **身份驗證**: 100-300 毫秒

### 速率限制指導原則
- 對分析請求實施 3 秒防抖
- 本地快取用戶資料
- 顯示載入狀態以改善使用者體驗

### 錯誤處理範例
```typescript
const handleError = (error: string) => {
  if (error.includes('5000 characters')) {
    return '條目太長。請保持在 5000 字元以內。';
  }
  if (error.includes('token')) {
    return '請重新登入。';
  }
  if (error.includes('rate limit')) {
    return '請求太頻繁。請稍等片刻。';
  }
  return '發生錯誤。請稍後再試。';
};
```

---

## 📚 實際使用範例

### React 組件範例
```typescript
import React, { useState } from 'react';
import { useMindWeaveAPI } from './hooks/useMindWeaveAPI';

const MindWeaveAnalyzer: React.FC = () => {
  const [entryText, setEntryText] = useState('');
  const [result, setResult] = useState<any>(null);
  
  const { analyzeEntry, loading, error } = useMindWeaveAPI({
    baseUrl: 'https://mind-be-ruddy.vercel.app',
    // authToken: localStorage.getItem('mindweave_token') // 如果用戶已登入
  });

  const handleAnalyze = async () => {
    if (!entryText.trim()) return;
    
    const result = await analyzeEntry({ entry_text: entryText });
    if (result) {
      setResult(result);
    }
  };

  return (
    <div className="mindweave-analyzer">
      <textarea
        value={entryText}
        onChange={(e) => setEntryText(e.target.value)}
        placeholder="你今天感覺如何？"
        maxLength={5000}
        rows={4}
        className="w-full p-3 border rounded"
      />
      
      <button
        onClick={handleAnalyze}
        disabled={loading || !entryText.trim()}
        className="mt-2 px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
      >
        {loading ? '分析中...' : '分析條目'}
      </button>

      {error && (
        <div className="mt-2 p-2 bg-red-100 text-red-700 rounded">
          錯誤: {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="p-3 bg-blue-50 rounded">
            <h3 className="font-bold">情緒分析:</h3>
            {Object.entries(result.analysis.emotions_quantified).map(([emotion, value]) => (
              <div key={emotion} className="flex justify-between">
                <span>{emotion}:</span>
                <span>{Math.round(value * 100)}%</span>
              </div>
            ))}
          </div>

          <div className="p-3 bg-green-50 rounded">
            <h3 className="font-bold">MindWeave 洞察:</h3>
            <p>{result.mindweave_reflection}</p>
          </div>

          {result.ysym && (
            <div className="p-3 bg-purple-50 rounded">
              <h3 className="font-bold">深度分析 (YSYM):</h3>
              <p>{result.ysym_analysis}</p>
            </div>
          )}

          <div className="text-sm text-gray-500">
            模式: {result.mode} | 處理時間: {result.processing_time}秒
          </div>
        </div>
      )}
    </div>
  );
};

export default MindWeaveAnalyzer;
```

---

## 🔧 開發環境設置

### 環境變數配置
```bash
# .env.local (Next.js) 或 .env (React)
NEXT_PUBLIC_MINDWEAVE_API_URL=https://mind-be-ruddy.vercel.app
NEXT_PUBLIC_MINDWEAVE_API_VERSION=v0.2.0
```

### TypeScript 類型定義
```typescript
// types/mindweave.ts
export interface EmotionAnalysis {
  emotions_quantified: Record<string, number>;
  emotion_polarity: {
    positive: number;
    negative: number;
  };
  topics: string[];
  timestamp: string;
}

export interface AnalysisResponse {
  analysis: EmotionAnalysis;
  mindweave_reflection: string;
  ysym: boolean;
  ysym_analysis?: string;
  mode: 'guest' | 'user';
  stored: boolean;
  processing_time: number;
  historical_entries_used?: number;
  message?: string;
  benefits?: string[];
}

export interface SearchResult {
  entry_id: string;
  entry_text: string;
  created_at: string;
  emotions_quantified: Record<string, number>;
  topics: string[];
  relevance_score: number;
}

export interface User {
  user_id: string;
  email?: string;
  username?: string;
  display_name?: string;
  plan_type: 'free' | 'pro';
  created_at: string;
}

export interface AuthResponse {
  user: User;
  tokens: {
    access_token: string;
    refresh_token: string;
  };
  message: string;
}
```

---

## 📱 移動端考慮事項

### Fetch API 配置
```typescript
// 適用於移動端的 fetch 配置
const fetchWithTimeout = async (url: string, options: RequestInit, timeout = 10000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};
```

### 離線支援
```typescript
// 檢查網路狀態
const isOnline = navigator.onLine;

// 離線時儲存分析請求
const queueAnalysisRequest = (request: AnalysisRequest) => {
  const queue = JSON.parse(localStorage.getItem('mindweave_queue') || '[]');
  queue.push(request);
  localStorage.setItem('mindweave_queue', JSON.stringify(queue));
};

// 網路恢復時處理佇列
const processQueue = async () => {
  const queue = JSON.parse(localStorage.getItem('mindweave_queue') || '[]');
  for (const request of queue) {
    try {
      await analyzeEntry(request);
    } catch (error) {
      console.error('Failed to process queued request:', error);
    }
  }
  localStorage.removeItem('mindweave_queue');
};
```

---

## 🚀 部署建議

### 環境配置
- **開發環境**: `http://localhost:3000`
- **測試環境**: `https://mind-be-staging.vercel.app`
- **生產環境**: `https://mind-be-ruddy.vercel.app`

### 安全考量
- 永遠不要在前端暴露 Supabase 或 Gemini API 密鑰
- 使用 HTTPS 進行所有 API 通訊
- 實施適當的 CORS 設置
- 定期輪換 JWT 密鑰

---

## 📞 支援與問題回報

**作者**: Gary Yang  
**電子郵件**: gary@agryyang.in  
**代碼庫**: https://github.com/Gary0302/Mind_BE  
**問題回報**: https://github.com/Gary0302/Mind_BE/issues

### 回報 API 問題時請包含
- 使用的端點和 HTTP 方法
- 請求標頭和內容（已移除敏感資訊）
- 完整的錯誤回應
- 重現步驟
- 瀏覽器/環境資訊

---
