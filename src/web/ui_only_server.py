#!/usr/bin/env python3
"""
Qalia UI Recording Server

A lightweight web server that handles ONLY the UI recording functionality.
This is completely separate from the AI exploration service.

This server provides:
- GitHub OAuth authentication
- Repository listing
- Recording session management
- WebSocket interface for real-time recording
- Test case storage and management

It does NOT include the AI exploration framework.
"""

import os
import time
import logging
import secrets
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

import uvicorn
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Cookie, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID", "Ov23lic8QQdOIc5gxuHz")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "18573be035c9560fea614f37a7bf8c709f11bf31")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/callback")

# Simple in-memory storage (in production, use proper database)
sessions = {}
oauth_states = {}
recording_sessions = {}


class GitHubOAuth:
    """Lightweight GitHub OAuth for UI only."""
    
    def __init__(self):
        self.client_id = GITHUB_CLIENT_ID
        self.client_secret = GITHUB_CLIENT_SECRET
        self.redirect_uri = GITHUB_REDIRECT_URI
        self.scope = "repo user:email"
    
    def generate_auth_url(self):
        """Generate GitHub OAuth authorization URL."""
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
        logger.info(f"Generated OAuth URL with state: {state[:8]}...")
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str):
        """Exchange authorization code for access token."""
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
            
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            return access_token
    
    async def get_user_info(self, access_token: str):
        """Get user information from GitHub API."""
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
            
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next((email["email"] for email in emails if email["primary"]), None)
                if primary_email:
                    user_data["email"] = primary_email
            
            return user_data

    async def get_user_repositories(self, access_token: str):
        """Get user repositories from GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={
                    "visibility": "all",
                    "sort": "updated",
                    "per_page": 50
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch repositories")
            
            return response.json()


def create_session(user_data, access_token):
    """Create a user session."""
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
    """Get session by ID."""
    if not session_id or session_id not in sessions:
        return None
    
    session = sessions[session_id]
    if datetime.utcnow() > session["expires_at"]:
        del sessions[session_id]
        return None
    
    session["last_activity"] = datetime.utcnow()
    return session


# Create FastAPI app
app = FastAPI(title="Qalia UI Recording Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GitHub OAuth
github_oauth = GitHubOAuth()

# Active WebSocket connections for recording
active_connections: Dict[str, WebSocket] = {}

# OAuth Routes
@app.get("/api/auth/login")
async def github_login():
    """Initiate GitHub OAuth login."""
    try:
        logger.info("Initiating GitHub OAuth login...")
        auth_url, state = github_oauth.generate_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@app.get("/api/auth/callback")
async def github_callback(code: str, state: str, response: Response):
    """Handle GitHub OAuth callback."""
    try:
        logger.info("GitHub OAuth callback received")
        
        # Basic state validation (can be enhanced)
        if state not in oauth_states:
            logger.warning(f"Invalid state parameter: {state[:8]}...")
            # In development, allow it to proceed
        
        # Exchange code for access token
        access_token = await github_oauth.exchange_code_for_token(code)
        
        # Get user information
        user_data = await github_oauth.get_user_info(access_token)
        
        # Create session
        session_id = create_session(user_data, access_token)
        
        # Set session cookie
        response.set_cookie(
            key="qalia_session",
            value=session_id,
            max_age=24 * 60 * 60,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        # Redirect to UI
        return RedirectResponse(url="/", status_code=302)
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@app.post("/api/auth/logout")
async def logout(response: Response, qalia_session: Optional[str] = Cookie(None)):
    """Logout user."""
    if qalia_session and qalia_session in sessions:
        del sessions[qalia_session]
    
    response.delete_cookie(key="qalia_session")
    return {"message": "Logged out successfully"}


@app.get("/api/auth/user")
async def get_user(qalia_session: Optional[str] = Cookie(None)):
    """Get current user info."""
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
    """List user's GitHub repositories."""
    session = get_session(qalia_session)
    
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        repositories = await github_oauth.get_user_repositories(session['access_token'])
        return {"repositories": repositories}
    except Exception as e:
        logger.error(f"Failed to fetch repositories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch repositories")


@app.get("/api/repos/{owner}/{repo}/sessions")
async def list_recording_sessions(owner: str, repo: str, qalia_session: Optional[str] = Cookie(None)):
    """List recording sessions for a repository."""
    session = get_session(qalia_session)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    repo_key = f"{owner}/{repo}"
    sessions_list = recording_sessions.get(repo_key, [])
    
    return {"sessions": sessions_list, "repository": repo_key}


@app.post("/api/repos/{owner}/{repo}/sessions")
async def create_recording_session(owner: str, repo: str, request: Request, qalia_session: Optional[str] = Cookie(None)):
    """Create a new recording session."""
    session = get_session(qalia_session)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    data = await request.json()
    
    session_id = f"session_{session['user']['id']}_{owner}_{repo}_{int(time.time())}"
    repo_key = f"{owner}/{repo}"
    
    recording_session = {
        "session_id": session_id,
        "status": "created",
        "repository": repo_key,
        "user": session['user']['login'],
        "created_at": datetime.utcnow().isoformat(),
        "data": data
    }
    
    if repo_key not in recording_sessions:
        recording_sessions[repo_key] = []
    recording_sessions[repo_key].append(recording_session)
    
    return recording_session


# WebSocket endpoint for real-time recording
@app.websocket("/ws/recording/{session_id}")
async def recording_websocket(websocket: WebSocket, session_id: str):
    """Handle real-time recording WebSocket connections."""
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        logger.info(f"Recording WebSocket connected for session: {session_id}")
        
        while True:
            data = await websocket.receive_json()
            await handle_recording_message(session_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"Recording WebSocket disconnected for session: {session_id}")
        if session_id in active_connections:
            del active_connections[session_id]
    except Exception as e:
        logger.error(f"Error in recording WebSocket for session {session_id}: {e}")
        if session_id in active_connections:
            del active_connections[session_id]


async def handle_recording_message(session_id: str, message: Dict[str, Any]):
    """Process recording messages from the client."""
    message_type = message.get("type")
    
    if message_type == "action_recorded":
        action_data = message.get("action", {})
        logger.info(f"Action recorded in session {session_id}: {action_data}")
        
        # Echo back confirmation
        await send_to_session(session_id, {
            "type": "action_confirmed",
            "action_id": action_data.get("id"),
            "timestamp": action_data.get("timestamp")
        })
        
    elif message_type == "recording_started":
        logger.info(f"Recording started for session: {session_id}")
        
    elif message_type == "recording_stopped":
        logger.info(f"Recording stopped for session: {session_id}")


async def send_to_session(session_id: str, message: Dict[str, Any]):
    """Send a message to a specific recording session."""
    if session_id in active_connections:
        try:
            await active_connections[session_id].send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {e}")
            if session_id in active_connections:
                del active_connections[session_id]


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"message": "Qalia UI Recording Server", "status": "running"}


# Serve built React app
# Try Docker path first, then local development path
ui_dist_path = Path("./ui/dist")
if not ui_dist_path.exists():
    ui_dist_path = Path(__file__).parent.parent.parent / "ui" / "dist"

if ui_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=ui_dist_path / "assets"), name="assets")
    
    @app.get("/ui/{path:path}")
    async def serve_ui(path: str = ""):
        """Serve built React app."""
        if path and (ui_dist_path / path).exists():
            return FileResponse(ui_dist_path / path)
        return FileResponse(ui_dist_path / "index.html")


# Serve main HTML file - catch-all route MUST be last
@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_frontend(path: str = ""):
    """Serve the React frontend."""
    try:
        if not ui_dist_path.exists() or not (ui_dist_path / "index.html").exists():
            raise HTTPException(status_code=404, detail="Frontend not built")
        return FileResponse(ui_dist_path / "index.html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Frontend not built")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting Qalia UI Recording Server on port {port}")
    logger.info("📱 This is the USER-FACING recording interface")
    logger.info("🤖 The AI exploration service is separate")
    
    # Debug path information
    logger.info(f"📁 Looking for UI dist at: {ui_dist_path.absolute()}")
    logger.info(f"📁 UI dist exists: {ui_dist_path.exists()}")
    if ui_dist_path.exists():
        logger.info(f"📁 Index.html exists: {(ui_dist_path / 'index.html').exists()}")
        logger.info(f"📁 Assets dir exists: {(ui_dist_path / 'assets').exists()}")
    
    uvicorn.run(
        "ui_only_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    ) 