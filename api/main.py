"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
  title='Personalized Conference Paper Explorer',
  description='A web app to rank conference papers by semantic similarity',
  version='1.0.0',
)

# Configure CORS for frontend
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    'http://localhost:3000',
    'http://localhost:5173',
  ],  # React dev servers
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)


@app.get('/api/health')
async def health_check():
  """Health check endpoint."""
  return {'status': 'ok', 'message': 'API is running'}


@app.get('/')
async def root():
  """Root endpoint."""
  return {'message': 'Personalized Conference Paper Explorer API'}
