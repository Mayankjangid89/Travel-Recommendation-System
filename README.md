# 🧳 Travel AI Agent - Meta Travel Package Recommender

> **Production-grade AI system** that aggregates travel packages from multiple agencies, normalizes data, and recommends the best options using intelligent ranking.

## 🎯 What This System Does

1. **Understands** natural language travel queries
2. **Discovers** travel agencies automatically
3. **Scrapes** packages from hundreds of sources
4. **Normalizes** data into a unified schema
5. **Ranks** packages using AI-powered scoring
6. **Recommends** top 5 options with explanations

## 🏗️ Architecture

```
User Query → Intent Parser → Trip Planner → Package Search (DB/Scraping)
→ Normalization → Filtering → Ranking → AI Response → User
```

**Background Workers**: Continuously scrape agencies and update database

## 📦 Tech Stack

- **Backend**: FastAPI + Python 3.13
- **Database**: PostgreSQL (SQLite for dev)
- **Cache**: Redis
- **Queue**: Celery + Redis
- **Scraping**: BeautifulSoup, Selenium, Playwright
- **LLM**: OpenAI GPT-4 for response generation

## 🚀 Quick Start

### Prerequisites
- Python 3.13
- PostgreSQL or SQLite
- Redis (optional for dev)

### Installation

```powershell
# Clone repository
git clone <repo-url>
cd travel-ai-agent

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python db/session.py
```

### Run Development Server

```powershell
uvicorn api.server:app --reload
```

Visit: http://localhost:8000/docs for API documentation

## 📁 Project Structure

```
travel-ai-agent/
├── api/              # FastAPI routes and server
├── agents/           # Intent parsing, planning, ranking
├── tools/            # Scraping, normalization, caching
├── db/               # Database models and session
├── workers/          # Background scraping workers
├── tests/            # Unit and integration tests
├── logs/             # Application logs
└── cache/            # File cache storage
```

## 🔑 Key Features

### ✅ Automatic Agency Discovery
System finds travel agencies automatically using:
- Google/Bing search
- Travel directories
- Tourism board listings

### ✅ Multi-Strategy Scraping
- Static HTML (requests + BeautifulSoup)
- JavaScript sites (Selenium/Playwright)
- Retry logic with exponential backoff
- Rate limiting per domain

### ✅ Intelligent Ranking
Packages scored on:
- Destination match (30%)
- Duration match (20%)
- Budget alignment (25%)
- Trust score (10%)
- Reviews/ratings (10%)
- Inclusions (5%)

### ✅ Production Ready
- Type hints everywhere
- Comprehensive error handling
- Structured logging
- Unit test coverage
- Docker support
- Health monitoring

## 📊 Database Schema

### Tables
- `agencies` - Travel agency information
- `travel_packages` - Normalized package data
- `scraping_jobs` - Job execution tracking
- `user_queries` - Analytics and feedback

## 🔧 Configuration

Key environment variables:
- `DATABASE_URL` - Database connection
- `REDIS_URL` - Redis connection
- `SCRAPER_TIMEOUT` - Scraping timeout
- `OPENAI_API_KEY` - LLM API key

See `.env.example` for full configuration.

## 📈 API Endpoints

- `POST /api/recommend` - Get package recommendations
- `GET /api/agencies` - List all agencies
- `GET /api/health` - System health check
- `GET /api/stats` - System statistics

## 🧪 Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_parser.py -v
```

## 🐳 Docker Deployment

```powershell
docker-compose up -d
```

## 📝 Development Status

- [x] Day 1: Database schema & models
- [ ] Day 2: Intent parser & trip planner
- [ ] Day 3: Agency discovery engine
- [ ] Day 4: Scraper engine
- [ ] Day 5: Normalizer & filter
- [ ] Day 6: Ranking engine
- [ ] Day 7: FastAPI endpoints
- [ ] Day 8: Background workers
- [ ] Day 9: Production setup
- [ ] Day 10: MVP UI

## 📄 License

MIT

## 👥 Contributing

This is a production startup project. Contributions welcome via pull requests.