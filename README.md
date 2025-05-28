# Personalized Conference Paper Explorer

A single-user web application to rank conference papers by semantic similarity to your own "seed" papers, with cached summaries, basic filters, and fortnightly re-ranking.

## Features

- **Semantic Paper Ranking**: Upload seed papers and get conference papers ranked by similarity
- **Intelligent Summaries**: Cached AI-generated summaries for quick paper overview
- **Advanced Filtering**: Filter by year, author, venue, and keywords
- **Automated Processing**: Monthly ingestion and fortnightly re-ranking
- **Cost Effective**: Designed to run on Heroku Eco plan (~$0.19/month for AI services)

## Tech Stack

- **Backend**: Python 3.11, FastAPI
- **Frontend**: React (Vite), Tailwind CSS
- **PDF Processing**: PyMuPDF
- **Embeddings**: OpenAI text-embedding-3-large
- **Vector DB**: Pinecone
- **Database**: PostgreSQL
- **Storage**: AWS S3
- **Deployment**: Heroku

## Project Structure

```
├── api/                 # FastAPI backend
│   ├── __init__.py
│   ├── main.py         # FastAPI app entry point
│   ├── config.py       # Configuration management
│   ├── models.py       # Database models
│   └── database.py     # Database connection
├── frontend/           # React SPA (to be created)
├── tasks/              # Background job scripts
│   ├── __init__.py
│   └── cli.py         # CLI for ingestion and ranking
├── utils/              # Shared utilities
│   ├── __init__.py
│   ├── pdf_parser.py   # PDF text extraction
│   ├── embeddings.py   # OpenAI embedding client
│   ├── pinecone_client.py # Vector database client
│   └── s3_client.py    # AWS S3 operations
├── tests/              # Test suites
│   ├── __init__.py
│   └── test_api.py     # API tests
├── pyproject.toml      # Python dependencies
├── Procfile           # Heroku deployment
└── env.example        # Environment variables template
```

## Setup

### Prerequisites

- Python 3.11+
- uv package manager
- PostgreSQL
- OpenAI API key
- Pinecone account
- AWS S3 bucket

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd paper-ranker
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your actual API keys and configuration
   ```

4. Initialize the database:
   ```bash
   # Make sure PostgreSQL is running
   python -c "from api.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

### Development

1. Start the API server:
   ```bash
   uvicorn api.main:app --reload
   ```

2. Run tests:
   ```bash
   pytest
   ```

3. Use CLI tools:
   ```bash
   python tasks/cli.py --help
   python tasks/cli.py ingest
   python tasks/cli.py rank
   python tasks/cli.py status
   ```

## API Endpoints

- `GET /` - Root endpoint
- `GET /api/health` - Health check
- `POST /api/ingest` - Ingest papers from S3 (TODO)
- `GET /api/rank` - Get ranked papers (TODO)
- `GET /api/summary/{paper_id}` - Get paper summary (TODO)

## Deployment

### Heroku

1. Create Heroku app:
   ```bash
   heroku create your-app-name
   ```

2. Add PostgreSQL addon:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

3. Add Scheduler addon:
   ```bash
   heroku addons:create scheduler:standard
   ```

4. Set environment variables:
   ```bash
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set PINECONE_API_KEY=your_key
   # ... set all other variables from env.example
   ```

5. Deploy:
   ```bash
   git push heroku main
   ```

6. Set up scheduled tasks in Heroku Dashboard:
   - Monthly: `python tasks/cli.py ingest`
   - Fortnightly: `python tasks/cli.py rank`

## Contributing

1. Follow the coding standards defined in pyproject.toml
2. Use 2-space indentation
3. Add type hints to all functions
4. Write tests for new features
5. Update documentation

## License

[Add your license here] # paper-ranker
