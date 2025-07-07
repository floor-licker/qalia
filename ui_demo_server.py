#!/usr/bin/env python3
"""
Standalone Qalia UI Demo Server

A simplified version of the UI server for testing the authentication interface.
This doesn't include all the complex qalia dependencies.
"""

import os
import time
import secrets
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, Request, Cookie, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory session storage for demo
sessions = {}
oauth_states = {}

class DemoOAuth:
    """Simple OAuth demo that doesn't actually connect to GitHub"""
    
    def generate_auth_url(self):
        # For demo purposes, just return a mock URL
        return "https://github.com/login/oauth/authorize?client_id=demo&redirect_uri=http://localhost:8000/api/auth/callback&scope=repo%20user:email&state=demo_state", "demo_state"

def create_demo_session(user_data):
    """Create a demo session"""
    session_id = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    
    sessions[session_id] = {
        "session_id": session_id,
        "user": user_data,
        "created_at": now,
        "expires_at": now + timedelta(hours=24),
        "last_activity": now
    }
    
    return session_id

def get_session(session_id: str):
    """Get session by ID"""
    if not session_id or session_id not in sessions:
        return None
    
    session = sessions[session_id]
    if datetime.utcnow() > session["expires_at"]:
        del sessions[session_id]
        return None
    
    session["last_activity"] = datetime.utcnow()
    return session

# Create FastAPI app
app = FastAPI(title="Qalia UI Demo")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve UI - redirect to Vite dev server in development
@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Qalia UI - Development Mode</title>
            <script>
                // Redirect to Vite dev server
                window.location.href = 'http://localhost:3000';
            </script>
        </head>
        <body>
            <p>Redirecting to development server...</p>
            <p>If not redirected, please visit <a href="http://localhost:3000">http://localhost:3000</a></p>
        </body>
        </html>
    """)

# OAuth Routes (simplified for demo)
@app.get("/api/auth/login")
async def github_login():
    """Demo login - returns mock OAuth URL"""
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }
    
    # For demo, return a GitHub-like URL but with demo parameters
    auth_url = f"http://localhost:8000/api/auth/demo-callback?code=demo_code&state={state}"
    
    return {"auth_url": auth_url}

@app.get("/api/auth/demo-callback")
async def demo_callback(code: str, state: str, response: Response):
    """Demo callback that simulates successful OAuth"""
    
    # Validate state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    # Remove state (one-time use)
    del oauth_states[state]
    
    # Create demo user
    demo_user = {
        "id": "123456",
        "login": "demo-user",
        "name": "Demo User",
        "email": "demo@example.com",
        "avatar_url": "https://github.com/identicons/demo-user.png"
    }
    
    # Create session
    session_id = create_demo_session(demo_user)
    
    # Set cookie
    response.set_cookie(
        key="qalia_session",
        value=session_id,
        max_age=24 * 60 * 60,
        httponly=True,
        secure=False,
        samesite="lax"
    )
    
    return RedirectResponse(url="http://localhost:3000", status_code=302)

@app.post("/api/auth/logout")
async def logout(response: Response, qalia_session: Optional[str] = Cookie(None)):
    """Logout user"""
    if qalia_session and qalia_session in sessions:
        del sessions[qalia_session]
    
    response.delete_cookie(key="qalia_session")
    return {"message": "Logged out successfully"}

@app.get("/api/auth/user")
async def get_user(qalia_session: Optional[str] = Cookie(None)):
    """Get current user info"""
    session = get_session(qalia_session)
    
    if not session:
        return {"user": None, "authenticated": False}
    
    return {
        "user": session["user"],
        "authenticated": True,
        "session": {
            "created_at": session["created_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat(),
            "scope": "repo user:email"
        }
    }

@app.get("/api/repos")
async def list_repos(qalia_session: Optional[str] = Cookie(None)):
    """Demo repositories list"""
    session = get_session(qalia_session)
    
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Return demo repositories
    demo_repos = [
        {
            "id": 1,
            "name": "my-web-app",
            "full_name": "demo-user/my-web-app",
            "description": "A demo web application for testing",
            "private": False,
            "html_url": "https://github.com/demo-user/my-web-app",
            "clone_url": "https://github.com/demo-user/my-web-app.git",
            "default_branch": "main",
            "language": "JavaScript",
            "stargazers_count": 42,
            "forks_count": 7,
            "permissions": {"admin": True, "push": True, "pull": True},
            "owner": {
                "login": "demo-user",
                "avatar_url": "https://github.com/identicons/demo-user.png",
                "type": "User"
            }
        },
        {
            "id": 2,
            "name": "qalia-tests",
            "full_name": "demo-user/qalia-tests",
            "description": "Test repository for Qalia testing",
            "private": True,
            "html_url": "https://github.com/demo-user/qalia-tests",
            "clone_url": "https://github.com/demo-user/qalia-tests.git",
            "default_branch": "main",
            "language": "TypeScript",
            "stargazers_count": 15,
            "forks_count": 2,
            "permissions": {"admin": True, "push": True, "pull": True},
            "owner": {
                "login": "demo-user",
                "avatar_url": "https://github.com/identicons/demo-user.png",
                "type": "User"
            }
        }
    ]
    
    return {"repositories": demo_repos}

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sessions": len(sessions)
    }

if __name__ == "__main__":
    print("🚀 Starting Qalia UI Demo Server")
    print("📍 Backend: http://localhost:8000")
    print("📍 Frontend: http://localhost:3000 (start separately)")
    print("📍 Health: http://localhost:8000/health")
    print("")
    print("💡 To test OAuth flow:")
    print("   1. Visit http://localhost:3000")
    print("   2. Click 'Sign in with GitHub'")
    print("   3. You'll be redirected to a demo OAuth flow")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 