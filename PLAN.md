Based on the design document, here's a detailed sequence of steps to implement the Personalized Conference Paper Explorer app:

## Phase 1: Project Setup & Infrastructure

### 1.1 Project Structure Setup
1. Initialize project repository with proper directory structure:
   - `/api/` - FastAPI backend
   - `/frontend/` - React SPA  
   - `/tasks/` - Background job scripts
   - `/utils/` - Shared utilities (PDF parser, embedding client, etc.)
   - `/tests/` - Test suites
   - Root config files (pyproject.toml, requirements.txt, etc.)

2. Set up Python environment with uv package manager
3. Configure code formatting tools (Ruff, Black) per pyproject.toml
4. Initialize React frontend with Vite and Tailwind CSS

### 1.2 External Services Setup
1. **AWS S3**:
   - Create S3 bucket `my-app-papers`
   - Set up folder structure (`seeds/`, `corpus/`)
   - Create IAM user with S3 permissions
   - Configure CORS for frontend uploads

2. **Pinecone**:
   - Create Pinecone account and get API key
   - Set up vector index named `papers` with 3072 dimensions
   - Configure metadata schema

3. **OpenAI**:
   - Set up OpenAI API account
   - Get API key for embeddings and chat completions

4. **Heroku**:
   - Create Heroku app
   - Add Postgres addon (hobby-dev tier)
   - Add Scheduler addon
   - Configure environment variables

## Phase 2: Backend Core Development

### 2.1 Database Schema & Models
1. Design and implement Postgres schema:
   - `papers` table (paper_id, title, authors, year, venue, keywords, s3_key)
   - `summaries` table (paper_id, summary, generated_at)
2. Create SQLAlchemy/Pydantic models for data validation
3. Set up database migrations and connection management

### 2.2 Utility Modules
1. **PDF Processing Utility** (`utils/pdf_parser.py`):
   - PyMuPDF integration for text extraction
   - Text chunking logic (10,000 tokens per chunk)
   - Metadata extraction (title, authors, year if available)

2. **Embedding Client** (`utils/embeddings.py`):
   - OpenAI API wrapper for text-embedding-3-large
   - Batch processing for efficiency
   - Error handling and retry logic

3. **Vector Database Client** (`utils/pinecone_client.py`):
   - Pinecone connection and operations
   - Batch upsert functionality
   - Query operations for similarity search

4. **S3 Client** (`utils/s3_client.py`):
   - File upload/download operations
   - List objects functionality
   - Presigned URL generation for frontend uploads

### 2.3 Core API Endpoints
1. **Health Check** (`GET /api/health`):
   - Basic status and uptime reporting

2. **Ingestion Endpoint** (`POST /api/ingest`):
   - List S3 objects in seeds/ and corpus/
   - Download and parse PDFs
   - Generate embeddings for text chunks
   - Upsert to Pinecone and Postgres
   - Progress tracking and error handling

3. **Ranking Endpoint** (`GET /api/rank`):
   - Fetch seed and corpus vectors from Pinecone
   - Compute cosine similarity scores
   - Apply filters (year, author, keywords)
   - Return sorted results with metadata

4. **Summary Endpoint** (`GET /api/summary/{paperId}`):
   - Check cache in Postgres summaries table
   - If miss: retrieve paper content, call OpenAI API
   - Store and return summary

5. **Upload Endpoint** (`POST /api/upload`):
   - Handle file uploads to S3
   - Validate PDF format
   - Return upload status

## Phase 3: Background Tasks Development

### 3.1 Task Infrastructure
1. Create `tasks.py` module with CLI interface
2. Implement logging and error reporting to Sentry
3. Add progress tracking and status updates

### 3.2 Ingestion Task
1. Headless version of ingestion logic
2. Comprehensive error handling and recovery
3. Performance optimization for large batches
4. Email/notification on completion

### 3.3 Ranking Task  
1. Pre-compute similarity scores
2. Optional summary pre-generation
3. Cache results for faster API responses
4. Cleanup old cached data

## Phase 4: Frontend Development

### 4.1 Core Components Setup
1. Set up React Router for navigation
2. Configure Tailwind CSS theme and components
3. Create reusable UI components (buttons, forms, cards)
4. Set up state management (Context API or Zustand)

### 4.2 Upload Interface
1. **Upload Page**:
   - Drag-and-drop interface for PDFs
   - Separate sections for seeds vs corpus papers
   - Upload progress indicators
   - File validation and error display

2. **Upload Components**:
   - File picker with PDF filtering
   - Upload progress bars
   - Success/error notifications

### 4.3 Dashboard Interface
1. **Paper List Component**:
   - Ranked paper display with scores
   - Paper card layout (title, authors, year, venue)
   - Pagination for large result sets

2. **Filtering System**:
   - Search input for title/author/venue
   - Year range slider
   - Keyword tags filtering
   - Real-time filter application

3. **Summary Modal/Panel**:
   - On-demand summary loading
   - Caching of loaded summaries
   - Summary regeneration option

### 4.4 Control Interface
1. **Status Dashboard**:
   - Last ingestion timestamp
   - System status indicators
   - Manual trigger buttons

2. **Action Buttons**:
   - "Re-rank papers" functionality
   - "Regenerate summaries" option
   - Manual ingestion trigger

## Phase 5: Integration & Testing

### 5.1 API Integration
1. Set up Axios or Fetch client for API calls
2. Implement error handling and retry logic
3. Add loading states and user feedback
4. Test all API endpoints with frontend

### 5.2 Testing Suite
1. **Backend Tests**:
   - Unit tests for utility functions
   - Integration tests for API endpoints
   - Mock external services (OpenAI, Pinecone)
   - Database operation tests

2. **Frontend Tests**:
   - Component unit tests
   - Integration tests for user workflows
   - E2E tests for critical paths

### 5.3 Performance Optimization
1. Implement caching strategies
2. Optimize database queries
3. Add request/response compression
4. Frontend bundle optimization

## Phase 6: Deployment & DevOps

### 6.1 Containerization (Optional)
1. Create Dockerfile for backend
2. Set up multi-stage builds
3. Configure for Heroku deployment

### 6.2 CI/CD Pipeline
1. **GitHub Actions Setup**:
   - Lint and format checking (Ruff, Black)
   - Run test suites
   - Build frontend assets
   - Deploy to Heroku on main branch

2. **Environment Management**:
   - Staging environment setup
   - Environment variable management
   - Secret management in GitHub

### 6.3 Heroku Configuration
1. Configure Procfile for web dyno
2. Set up environment variables
3. Configure Heroku Scheduler jobs:
   - Monthly ingestion task
   - Fortnightly ranking task
4. Set up database migrations

## Phase 7: Monitoring & Maintenance

### 7.1 Monitoring Setup
1. **Sentry Integration**:
   - Error tracking for backend and frontend
   - Performance monitoring
   - Alert configuration

2. **Logging**:
   - Structured logging implementation
   - Log aggregation setup (LogDNA)
   - Log retention policies

### 7.2 Health Monitoring
1. Application health checks
2. Database connection monitoring
3. External service availability checks
4. Automated alerting on failures

## Phase 8: Documentation & Launch

### 8.1 Documentation
1. API documentation (OpenAPI/Swagger)
2. User guide for paper uploads and usage
3. Deployment and maintenance guides
4. Troubleshooting documentation

### 8.2 Launch Preparation
1. Load testing with sample data
2. Security review and hardening
3. Backup and recovery procedures
4. Launch checklist and rollback plan

This sequence provides a comprehensive roadmap for implementing the entire application, from initial setup through production deployment and ongoing maintenance.
