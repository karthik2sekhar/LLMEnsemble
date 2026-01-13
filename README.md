# LLM Ensemble

A production-ready web application that queries multiple OpenAI LLM models in parallel and synthesizes their responses into a unified, comprehensive answer. Now with **intelligent query routing** for cost optimization, **Time-Travel Answers** for temporal questions, and **real-time streaming** for instant feedback!

![LLM Ensemble Architecture](https://via.placeholder.com/800x400?text=LLM+Ensemble+Architecture)

## 🚀 Features

- **Multi-Model Querying**: Query multiple OpenAI models (GPT-4 Turbo, GPT-4o, GPT-4o-mini, GPT-5.2) simultaneously
- **🆕 Intelligent Query Routing**: Automatically classifies queries and routes to optimal model combinations
- **🆕 Time-Travel Answers**: See how answers evolve over time for temporally sensitive questions
- **🆕 Streaming SSE**: Real-time Server-Sent Events for progressive result delivery (~8s to first result)
- **🆕 Temporal Awareness**: Automatic detection of time-sensitive queries
- **🆕 Real-time Web Search**: Perplexity API integration for current information
- **🆕 Parallel Snapshot Generation**: 65% faster time-travel with async parallel execution
- **Cost Optimization**: Smart routing saves 40-70% on simple/moderate queries
- **Intelligent Synthesis**: Automatically synthesizes responses into a coherent final answer
- **Real-time Progress**: Live progress indicators showing which models are responding
- **Response Caching**: 24-hour caching to avoid duplicate API calls
- **Classification Caching**: 24-hour caching for query classifications
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **Dark Mode**: Full dark mode support with system preference detection
- **Query History**: Local storage-based history of previous questions
- **Cost Tracking**: Real-time token usage and cost estimation with savings calculation
- **Responsive Design**: Works on mobile, tablet, and desktop

## ⏰ Time-Travel Answers

The application now features a "Time-Travel Answers" mode that shows how answers evolve over time for temporally sensitive questions.

### How It Works

1. **Temporal Sensitivity Classification**: Questions are classified as HIGH, MEDIUM, LOW, or NONE sensitivity
2. **Time Point Identification**: Optimal historical dates are selected based on the question topic
3. **Snapshot Generation**: Answers are generated for each time point as if responding on that date
4. **Evolution Analysis**: Key changes between periods are extracted and an evolution narrative is synthesized

### Temporal Sensitivity Levels

| Level | Description | Examples | Time-Travel |
|-------|-------------|----------|-------------|
| **HIGH** | Answer changes significantly | AI models, current events, market data | ✅ Applied |
| **MEDIUM** | Answer may evolve | Business strategies, industry standards | ✅ Applied |
| **LOW** | Relatively stable | Historical facts | ❌ Skipped |
| **NONE** | Timeless facts | Definitions, scientific laws | ❌ Skipped |

### Example Questions

| Question | Sensitivity | Time Points |
|----------|-------------|-------------|
| "What are the latest AI models?" | HIGH | 2023 → GPT-4o → Today |
| "Who is the US President?" | HIGH | 2021 → 2024 Election → Today |
| "What is photosynthesis?" | NONE | Skipped (timeless) |

## 📡 Real-Time Streaming (SSE)

The Time-Travel feature now supports **Server-Sent Events (SSE)** for progressive result delivery. Instead of waiting 30-40 seconds for all snapshots, users see results as they arrive.

### Performance Improvements

| Metric | Before (Sequential) | After (Parallel + Streaming) |
|--------|---------------------|------------------------------|
| Total Time | 90+ seconds | ~35 seconds |
| Time to First Result | 90+ seconds | **~8 seconds** |
| User Perceived Latency | Very High | Low |

### How Streaming Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streaming Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Client sends POST /api/time-travel-stream                   │
│                         │                                        │
│                         ▼                                        │
│  2. Server classifies question & identifies time points         │
│                         │                                        │
│                         ▼                                        │
│  3. Server sends SSE: classification event                      │
│                         │                                        │
│                         ▼                                        │
│  4. Parallel async tasks generate snapshots                     │
│     ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│     │ 2020-01 │  │ 2022-06 │  │ 2024-01 │  │ Current │         │
│     └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │
│          │            │            │            │                │
│          ▼            ▼            ▼            ▼                │
│  5. SSE events sent as each snapshot completes (first ~8s)      │
│                         │                                        │
│                         ▼                                        │
│  6. Server sends SSE: narrative event (evolution summary)       │
│                         │                                        │
│                         ▼                                        │
│  7. Server sends SSE: complete event                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### SSE Event Types

| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `classification` | Query analysis result | `sensitivity`, `explanation`, `num_snapshots` |
| `snapshot` | Individual time period answer | `date_label`, `time_period`, `answer`, `insight` |
| `narrative` | Evolution summary | `narrative` (string) |
| `complete` | Stream finished | `total_snapshots`, `total_time` |
| `error` | Error occurred | `message`, `code` |

### Frontend Integration

The frontend uses a custom React hook `useTimeTravelStream` to consume the SSE stream:

```typescript
const {
  isStreaming,
  snapshots,      // Array of snapshots, progressively populated
  classification, // Query classification result
  narrative,      // Evolution narrative (arrives at end)
  error,
  startStream,
} = useTimeTravelStream();
```

### API Endpoint

**POST `/api/time-travel-stream`**

Returns a `text/event-stream` response with Server-Sent Events.

**Request:**
```json
{
  "question": "What are the best AI coding assistants?",
  "max_tokens": 2000,
  "temperature": 0.7
}
```

**SSE Response Stream:**
```
event: classification
data: {"sensitivity":"high","explanation":"AI tools evolve rapidly","num_snapshots":4}

event: snapshot
data: {"date_label":"January 2023","time_period":"2023-01","answer":"...","insight":"..."}

event: snapshot
data: {"date_label":"January 2024","time_period":"2024-01","answer":"...","insight":"..."}

event: narrative
data: {"narrative":"The landscape of AI coding assistants has evolved dramatically..."}

event: complete
data: {"total_snapshots":4,"total_time":35.2}
```

## 🧠 Intelligent Query Routing

The application now includes an intelligent query router that automatically classifies incoming queries and routes them to the optimal combination of models based on:

- **Complexity**: Simple, Moderate, or Complex
- **Intent**: Factual, Creative, Analytical, Procedural, or Comparative
- **Domain**: Coding, Technical, General, Creative, or Research

### Routing Logic

| Complexity | Models Used | Synthesis | Typical Savings |
|------------|-------------|-----------|-----------------|
| Simple | gpt-4o-mini only | No | 60-70% |
| Moderate | gpt-4o-mini + gpt-4o | No | 40-50% |
| Complex | All 3 models | Yes (GPT-5.2) | 0% |

### Example Classifications

| Query | Complexity | Routing |
|-------|------------|---------|
| "What is the capital of France?" | Simple | gpt-4o-mini |
| "Explain how photosynthesis works" | Moderate | gpt-4o-mini + gpt-4o |
| "Design a microservices architecture for e-commerce" | Complex | All models + synthesis |

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Question   │  │   Model     │  │    Results Display      │  │
│  │   Input     │  │  Selector   │  │  (Synthesis + Cards)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                         │                                        │
│        ┌────────────────┴────────────────┐                      │
│        ▼                                 ▼                      │
│  ┌─────────────┐               ┌─────────────────────┐          │
│  │ useEnsemble │               │ useTimeTravelStream │          │
│  │    Hook     │               │   Hook (SSE)        │          │
│  └─────────────┘               └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
           ▼                                     ▼
┌────────────────────────┐         ┌───────────────────────────────┐
│  REST API Endpoints    │         │  Streaming Endpoints (SSE)    │
│  /api/ensemble         │         │  /api/time-travel-stream      │
│  /api/route-and-answer │         └───────────────────────────────┘
└────────────────────────┘                       │
           │                                     │
           ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│  │   Routes    │  │     Services      │  │    Utilities      │  │
│  │  /ensemble  │  │  LLM Service      │  │  Redis Cache      │  │
│  │  /streaming │  │  Synthesis Svc    │  │  Rate Limiter     │  │
│  │  /router    │  │  Time Travel Svc  │  │  Monitoring       │  │
│  │  /monitor   │  │  Streaming TT Svc │  │  Logger           │  │
│  └─────────────┘  └───────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌──────────────────────────────┐    ┌────────────────────────────┐
│         OpenAI API           │    │       Perplexity API       │
│  ┌───────┐ ┌───────┐ ┌────┐  │    │  (Real-time Web Search)    │
│  │GPT-4o │ │ Mini  │ │5.2 │  │    └────────────────────────────┘
│  └───────┘ └───────┘ └────┘  │
└──────────────────────────────┘
```

## 📦 Prerequisites

- **Python 3.10+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **OpenAI API Key** - Required for LLM access
- **Docker** (optional) - For containerized deployment

## 🛠️ Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/llm-ensemble.git
cd llm-ensemble
```

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
```

## ⚙️ Configuration

### Backend Configuration (.env)

```env
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional
OPENAI_ORG_ID=org-your-org-id
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
HOST=0.0.0.0

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60

# Cache
CACHE_ENABLED=true
CACHE_TTL=86400

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Models
DEFAULT_MODELS=gpt-4-turbo,gpt-4o,gpt-4o-mini
SYNTHESIS_MODEL=gpt-4o
```

### Frontend Configuration (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚀 Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
# Activate virtual environment first
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the application at `http://localhost:3000`

### Using Docker Compose

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-api-key-here

# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

## 📚 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check endpoint |
| GET | `/api/models` | List available models |
| POST | `/api/ensemble` | Query multiple models and synthesize (full ensemble) |
| POST | `/api/route-and-answer` | 🆕 Intelligent routing - classifies and routes to optimal models |
| POST | `/api/time-travel-stream` | 🆕 **Streaming SSE** - Time-travel answers with real-time updates |
| POST | `/api/synthesize` | Synthesize pre-collected responses |
| GET | `/api/stats` | Get usage statistics |
| GET | `/api/routing-stats` | 🆕 Get routing statistics and cost savings |
| GET | `/api/monitoring/metrics` | 🆕 Prometheus-compatible metrics |
| GET | `/api/monitoring/health/detailed` | 🆕 Detailed health with dependencies |
| POST | `/api/clear-classification-cache` | 🆕 Clear classification cache |

### POST /api/route-and-answer (NEW)

Intelligently route a query to optimal models based on classification.

**Request:**
```json
{
  "question": "What is the capital of France?",
  "max_tokens": 2000,
  "temperature": 0.7,
  "override_models": null,
  "force_synthesis": null
}
```

**Response:**
```json
{
  "question": "What is the capital of France?",
  "classification": {
    "complexity": "simple",
    "intent": "factual",
    "domain": "general",
    "requires_search": false,
    "recommended_models": ["gpt-4o-mini"],
    "reasoning": "Simple factual lookup with a single definitive answer.",
    "confidence": 0.98
  },
  "routing_decision": {
    "models_to_use": ["gpt-4o-mini"],
    "use_synthesis": false,
    "synthesis_model": null,
    "estimated_cost": 0.0003,
    "estimated_time_seconds": 1.5,
    "routing_rationale": "Simple query: Using single fast model for cost efficiency."
  },
  "models_used": ["gpt-4o-mini"],
  "individual_responses": [...],
  "final_answer": "The capital of France is Paris.",
  "synthesis": null,
  "cost_breakdown": {
    "model_costs": {"gpt-4o-mini": 0.0002},
    "synthesis_cost": 0,
    "classification_cost": 0.00005,
    "total_cost": 0.00025,
    "full_ensemble_cost": 0.015,
    "savings": 0.01475,
    "savings_percentage": 98.3
  },
  "execution_metrics": {
    "classification_time_ms": 450,
    "model_execution_time_ms": {"gpt-4o-mini": 1200},
    "synthesis_time_ms": 0,
    "total_time_ms": 1650
  },
  "timestamp": "2026-01-09T00:00:00Z",
  "fallback_used": false,
  "fallback_reason": null
}
```

### POST /api/ensemble

Query multiple LLM models and get a synthesized response.

**Request:**
```json
{
  "question": "What are the key differences between REST and GraphQL?",
  "models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
  "max_tokens": 2000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "question": "What are the key differences between REST and GraphQL?",
  "model_responses": [
    {
      "model_name": "gpt-4-turbo",
      "response_text": "...",
      "tokens_used": {
        "prompt_tokens": 50,
        "completion_tokens": 500,
        "total_tokens": 550
      },
      "cost_estimate": 0.0165,
      "response_time_seconds": 3.5,
      "timestamp": "2026-01-08T12:00:00Z",
      "cache_status": "miss",
      "success": true
    }
  ],
  "synthesis": {
    "synthesized_answer": "## Summary\n\n...",
    "synthesis_model": "gpt-4o",
    "tokens_used": {...},
    "cost_estimate": 0.005,
    "response_time_seconds": 2.1,
    "timestamp": "2026-01-08T12:00:05Z",
    "model_contributions": {...}
  },
  "total_cost": 0.0315,
  "total_time_seconds": 5.6,
  "timestamp": "2026-01-08T12:00:00Z",
  "cached": false
}
```

### Interactive API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🧪 Testing

### Backend Tests

```bash
cd backend
# Activate virtual environment
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm run test
```

## 🚢 Deployment

### Vercel (Frontend)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Set environment variables:
   - `NEXT_PUBLIC_API_URL`: Your backend URL

### Railway/Heroku (Backend)

1. Create a new project
2. Connect your repository
3. Set environment variables:
   - `OPENAI_API_KEY`: Your API key
   - `CORS_ORIGINS`: Your frontend URL

### Docker Deployment

```bash
# Build images
docker build -t llm-ensemble-backend ./backend
docker build -t llm-ensemble-frontend ./frontend

# Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

## 📁 Project Structure

```
llm-ensemble/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Data models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ensemble.py      # Ensemble endpoints
│   │   │   ├── router.py        # Smart routing endpoints
│   │   │   ├── streaming.py     # 🆕 SSE streaming endpoints
│   │   │   ├── monitoring.py    # 🆕 Health & metrics
│   │   │   └── health.py        # Health check
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py           # LLM API calls
│   │   │   ├── synthesis_service.py     # Response synthesis
│   │   │   ├── router_service.py        # Query classification & routing
│   │   │   ├── time_travel_service.py   # Time-travel base service
│   │   │   ├── time_travel_service_optimized.py  # 🆕 Parallel execution
│   │   │   ├── streaming_time_travel.py # 🆕 SSE streaming service
│   │   │   ├── search_service.py        # Web search integration
│   │   │   └── perplexity_service.py    # Perplexity API
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── cache.py         # In-memory caching
│   │       ├── redis_cache.py   # 🆕 Redis cache layer
│   │       ├── monitoring.py    # 🆕 Metrics & tracing
│   │       └── logging.py       # Logging configuration
│   ├── tests/
│   │   ├── test_main.py
│   │   └── test_router.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── QuestionInput.tsx
│   │   │   ├── ResponseCard.tsx
│   │   │   ├── SynthesisResult.tsx
│   │   │   ├── TimeTravelTimeline.tsx
│   │   │   ├── StreamingTimeTravelTimeline.tsx  # 🆕 Streaming UI
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   ├── useEnsembleLLM.ts
│   │   │   └── useTimeTravelStream.ts    # 🆕 SSE hook
│   │   ├── pages/
│   │   │   ├── index.tsx
│   │   │   ├── _app.tsx
│   │   │   └── _document.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── k8s/                         # 🆕 Kubernetes configs
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── backend-deployment-optimized.yaml
│   ├── frontend-deployment.yaml
│   ├── hpa.yaml                 # Horizontal Pod Autoscaler
│   └── ingress.yaml
├── scripts/
│   ├── deploy.ps1               # Windows deployment
│   ├── deploy.sh                # Linux deployment
│   └── cleanup.ps1              # Cleanup scripts
├── docker-compose.yml
├── DEPLOYMENT.md                # Deployment guide
├── PERFORMANCE_OPTIMIZATION.md  # Performance tuning guide
└── README.md
```

## 🔧 Model Information

| Model | Specialty | Input Cost | Output Cost |
|-------|-----------|------------|-------------|
| gpt-4-turbo | Complex reasoning, detailed analysis | $0.01/1K | $0.03/1K |
| gpt-4o | Creative, multimodal capabilities | $0.005/1K | $0.015/1K |
| gpt-4o-mini | Fast, cost-efficient responses | $0.00015/1K | $0.0006/1K |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the GPT models
- FastAPI for the excellent Python web framework
- Next.js and React for the frontend framework
- Tailwind CSS for the styling utilities

---

Made with ❤️ by the LLM Ensemble Team
