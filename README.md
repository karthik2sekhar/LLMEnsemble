# LLM Ensemble

A production-ready web application that queries multiple OpenAI LLM models in parallel and synthesizes their responses into a unified, comprehensive answer.

![LLM Ensemble Architecture](https://via.placeholder.com/800x400?text=LLM+Ensemble+Architecture)

## 🚀 Features

- **Multi-Model Querying**: Query multiple OpenAI models (GPT-4 Turbo, GPT-4o, GPT-4o-mini) simultaneously
- **Intelligent Synthesis**: Automatically synthesizes responses into a coherent final answer
- **Real-time Progress**: Live progress indicators showing which models are responding
- **Response Caching**: 24-hour caching to avoid duplicate API calls
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **Dark Mode**: Full dark mode support with system preference detection
- **Query History**: Local storage-based history of previous questions
- **Cost Tracking**: Real-time token usage and cost estimation
- **Responsive Design**: Works on mobile, tablet, and desktop

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
│                         Frontend (Next.js)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Question   │  │   Model     │  │    Results Display      │  │
│  │   Input     │  │  Selector   │  │  (Synthesis + Cards)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routes    │  │  Services   │  │       Utilities         │  │
│  │  /ensemble  │──│  LLM Svc    │──│  Cache | Rate Limiter   │  │
│  │  /synthesize│  │  Synthesis  │  │  Logger                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OpenAI API                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ GPT-4 Turbo │  │   GPT-4o    │  │      GPT-4o-mini        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
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
| POST | `/api/ensemble` | Query multiple models and synthesize |
| POST | `/api/synthesize` | Synthesize pre-collected responses |
| GET | `/api/stats` | Get usage statistics |

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
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration management
│   │   ├── models.py         # Data models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ensemble.py   # Ensemble endpoints
│   │   │   └── health.py     # Health check
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py      # LLM API calls
│   │   │   └── synthesis_service.py # Response synthesis
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── cache.py      # Caching utilities
│   │       └── logging.py    # Logging configuration
│   ├── tests/
│   │   └── test_main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Next.js pages
│   │   ├── services/        # API service
│   │   ├── hooks/           # Custom hooks
│   │   └── styles/          # CSS styles
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
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
