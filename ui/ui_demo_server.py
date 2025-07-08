#!/usr/bin/env python3
"""
Standalone Qalia UI Demo Server

A simplified version of the UI server for testing the authentication interface.
This doesn't include all the complex qalia dependencies.
"""

import os
import secrets
import logging
from typing import Optional
from urllib.parse import urlencode
from datetime import datetime, timedelta
import httpx

import uvicorn
from fastapi import FastAPI, Request, Cookie, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = "Ov23lic8QQdOIc5gxuHz"
GITHUB_CLIENT_SECRET = "18573be035c9560fea614f37a7bf8c709f11bf31"
GITHUB_REDIRECT_URI = "http://157.245.241.244/api/auth/github/callback"

# Simple in-memory session storage
sessions = {}
oauth_states = {}

class GitHubOAuth:
    """Real GitHub OAuth implementation"""
    
    def __init__(self):
        self.client_id = GITHUB_CLIENT_ID
        self.client_secret = GITHUB_CLIENT_SECRET
        self.redirect_uri = GITHUB_REDIRECT_URI
        self.scope = "repo user:email"
    
    def generate_auth_url(self):
        """Generate real GitHub OAuth authorization URL"""
        state = secrets.token_urlsafe(32)
        
        # Store state for validation
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "allow_signup": "true"
        }
        
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str):
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = response.json()
            
            if "error" in token_data:
                raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth error"))
            
            return token_data.get("access_token")
    
    async def get_user_info(self, access_token: str):
        """Get user information from GitHub API"""
        async with httpx.AsyncClient() as client:
            # Get user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            user_data = user_response.json()
            
            # Get user emails
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            emails = []
            if emails_response.status_code == 200:
                emails = emails_response.json()
                # Find primary email
                primary_email = next((email["email"] for email in emails if email["primary"]), None)
                if primary_email:
                    user_data["email"] = primary_email
            
            return user_data

def create_session(user_data, access_token):
    """Create a session"""
    session_id = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    
    sessions[session_id] = {
        "session_id": session_id,
        "user": user_data,
        "access_token": access_token,
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
app = FastAPI(title="Qalia UI")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://157.245.241.244", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GitHub OAuth
github_oauth = GitHubOAuth()

# OAuth Routes
@app.get("/api/auth/login")
async def github_login():
    """Initiate GitHub OAuth login"""
    try:
        auth_url, state = github_oauth.generate_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")

@app.get("/api/auth/github/callback")
async def github_callback(code: str, state: str, response: Response):
    """Handle GitHub OAuth callback"""
    try:
        # Validate state
        if state not in oauth_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Check if state is expired
        state_data = oauth_states[state]
        if datetime.utcnow() > state_data["expires_at"]:
            del oauth_states[state]
            raise HTTPException(status_code=400, detail="State parameter expired")
        
        # Remove state (one-time use)
        del oauth_states[state]
        
        # Exchange code for access token
        access_token = await github_oauth.exchange_code_for_token(code)
        
        # Get user information
        user_data = await github_oauth.get_user_info(access_token)
        
        # Create session
        session_id = create_session(user_data, access_token)
        
        # Set secure cookie
        response.set_cookie(
            key="qalia_session",
            value=session_id,
            max_age=24 * 60 * 60,
            httponly=True,
            secure=True,  # Enable for HTTPS
            samesite="lax"
        )
        
        # Redirect to frontend
        return RedirectResponse(url="http://157.245.241.244", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

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
    """List user's GitHub repositories"""
    session = get_session(qalia_session)
    
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {session['access_token']}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={
                    "visibility": "all",
                    "sort": "updated",
                    "per_page": 50
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch repositories")
            
            return response.json()
            
    except Exception as e:
        logger.error(f"Failed to fetch repositories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch repositories")

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "qalia-ui",
        "oauth": "github-production"
    }

# Serve static files (built frontend) - AFTER API routes to avoid conflicts
app.mount("/assets", StaticFiles(directory="ui/dist/assets"), name="assets")

# Serve favicon
@app.get("/vite.svg")
async def serve_favicon():
    return FileResponse("ui/dist/vite.svg")

# Serve main HTML file - catch-all route MUST be last
@app.get("/", response_class=HTMLResponse)
@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_frontend(path: str = ""):
    """Serve the React frontend"""
    try:
        return FileResponse("ui/dist/index.html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Frontend not built")

if __name__ == "__main__":
    logger.info("🚀 Starting Qalia UI with GitHub OAuth")
    logger.info(f"📍 Application: http://157.245.241.244")
    logger.info(f"📍 OAuth Callback: {GITHUB_REDIRECT_URI}")
    logger.info("🔐 Using production GitHub OAuth")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 