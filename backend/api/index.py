"""Vercel serverless entrypoint — wraps FastAPI app."""
from app.main import app

# Vercel expects a default export
handler = app
