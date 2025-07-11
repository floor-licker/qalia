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
import hashlib
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
import json
import traceback

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Set third-party loggers to WARNING to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Configuration with detailed logging
logger.info("🔧 Loading configuration...")
PORT = int(os.getenv("PORT", 8000))
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23lic8QQdOIc5gxuHz")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/github/callback")

logger.info(f"🔧 Configuration loaded:")
logger.info(f"   - Port: {PORT}")
logger.info(f"   - GitHub Client ID: {GITHUB_CLIENT_ID}")
logger.info(f"   - GitHub Secret: {'✓ Set' if GITHUB_CLIENT_SECRET else '❌ Missing'}")
logger.info(f"   - Redirect URI: {GITHUB_REDIRECT_URI}")

# In-memory session storage with detailed logging
sessions: Dict[str, Dict[str, Any]] = {}
oauth_states: Dict[str, Dict[str, Any]] = {}

def log_sessions_state():
    """Log current session state for debugging"""
    logger.info(f"📊 Session State: {len(sessions)} active sessions, {len(oauth_states)} pending OAuth states")
    for session_id, session_data in sessions.items():
        logger.info(f"   Session {session_id[:8]}...: user={session_data.get('user', {}).get('login', 'unknown')}, created={session_data.get('created_at', 'unknown')}")
    for state, state_data in oauth_states.items():
        logger.info(f"   OAuth State {state[:8]}...: created={state_data.get('created_at', 'unknown')}")

class GitHubOAuth:
    """Lightweight GitHub OAuth for UI only."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        logger.info(f"🔐 GitHub OAuth initialized with redirect URI: {redirect_uri}")
    
    def generate_auth_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL with detailed logging"""
        logger.info(f"🔗 Generating GitHub OAuth URL with state: {state[:8]}...")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo user:email",
            "state": state,
            "allow_signup": "true"
        }
        
        logger.info(f"🔗 OAuth parameters:")
        for key, value in params.items():
            if key == "state":
                logger.info(f"   - {key}: {value[:8]}...")
            else:
                logger.info(f"   - {key}: {value}")
        
        base_url = "https://github.com/login/oauth/authorize"
        url = f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        logger.info(f"🔗 Generated OAuth URL: {url}")
        return url
    
    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange authorization code for access token with comprehensive logging"""
        logger.info(f"🔄 Starting token exchange for code: {code[:8]}...")
        
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        logger.info(f"🔄 Token exchange request:")
        logger.info(f"   - client_id: {self.client_id}")
        logger.info(f"   - client_secret: {'✓ Set' if self.client_secret else '❌ Missing'}")
        logger.info(f"   - code: {code[:8]}...")
        logger.info(f"   - redirect_uri: {self.redirect_uri}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("🔄 Sending token exchange request to GitHub...")
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data=token_data
                )
                
                logger.info(f"🔄 GitHub token response: {response.status_code}")
                logger.info(f"🔄 GitHub token response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    logger.error(f"❌ Token exchange failed: HTTP {response.status_code}")
                    logger.error(f"❌ Response body: {response.text}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to exchange code for token: HTTP {response.status_code}"
                    )
                
                response_data = response.json()
                logger.info(f"🔄 Token exchange response data: {response_data}")
                
                if "error" in response_data:
                    logger.error(f"❌ GitHub OAuth error: {response_data}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"GitHub OAuth error: {response_data.get('error_description', response_data.get('error'))}"
                    )
                
                access_token = response_data.get("access_token")
                if not access_token:
                    logger.error(f"❌ No access token in response: {response_data}")
                    raise HTTPException(status_code=400, detail="No access token received from GitHub")
                
                logger.info(f"✅ Token exchange successful! Token: {access_token[:8]}...")
                return access_token
                
        except httpx.TimeoutException:
            logger.error("❌ Token exchange timed out")
            raise HTTPException(status_code=400, detail="Token exchange timed out")
        except httpx.RequestError as e:
            logger.error(f"❌ Token exchange request failed: {e}")
            raise HTTPException(status_code=400, detail=f"Token exchange request failed: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during token exchange: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during token exchange: {e}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub with comprehensive logging"""
        logger.info(f"👤 Fetching user info with token: {access_token[:8]}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("👤 Sending user info request to GitHub...")
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                logger.info(f"👤 GitHub user response: {response.status_code}")
                logger.info(f"👤 GitHub user response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    logger.error(f"❌ User info fetch failed: HTTP {response.status_code}")
                    logger.error(f"❌ Response body: {response.text}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to get user info: HTTP {response.status_code}"
                    )
                
                user_data = response.json()
                logger.info(f"👤 User data received: {user_data}")
                logger.info(f"👤 User: {user_data.get('login')} ({user_data.get('name', 'No name')})")
                
                return user_data
                
        except httpx.TimeoutException:
            logger.error("❌ User info fetch timed out")
            raise HTTPException(status_code=400, detail="User info fetch timed out")
        except httpx.RequestError as e:
            logger.error(f"❌ User info request failed: {e}")
            raise HTTPException(status_code=400, detail=f"User info request failed: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during user info fetch: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during user info fetch: {e}")

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


def create_session(user_data: Dict[str, Any], access_token: str) -> str:
    """Create a new session with detailed logging"""
    session_id = secrets.token_urlsafe(32)
    session_data = {
        "user": user_data,
        "access_token": access_token,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    sessions[session_id] = session_data
    
    logger.info(f"🆕 Created new session: {session_id[:8]}...")
    logger.info(f"🆕 Session data: user={user_data.get('login')}, expires={session_data['expires_at']}")
    log_sessions_state()
    
    return session_id

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data with detailed logging"""
    logger.info(f"🔍 Looking up session: {session_id[:8]}...")
    
    if session_id not in sessions:
        logger.warning(f"❌ Session not found: {session_id[:8]}...")
        log_sessions_state()
        return None
    
    session_data = sessions[session_id]
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    
    if datetime.now() > expires_at:
        logger.warning(f"⏰ Session expired: {session_id[:8]}... (expired at {expires_at})")
        del sessions[session_id]
        log_sessions_state()
        return None
    
    logger.info(f"✅ Session found: {session_id[:8]}... user={session_data.get('user', {}).get('login', 'unknown')}")
    return session_data

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from session with detailed logging"""
    logger.info("🔍 Checking current user from request...")
    
    # Check session cookie
    session_id = request.cookies.get("qalia_session")
    if not session_id:
        logger.info("❌ No session cookie found")
        return None
    
    logger.info(f"🍪 Session cookie found: {session_id[:8]}...")
    
    session_data = get_session(session_id)
    if not session_data:
        logger.warning("❌ Session data not found or expired")
        return None
    
    user_data = session_data.get("user")
    if user_data:
        logger.info(f"✅ Current user: {user_data.get('login')} ({user_data.get('name', 'No name')})")
    else:
        logger.warning("❌ No user data in session")
    
    return user_data


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
github_oauth = GitHubOAuth(GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI)

# Active WebSocket connections for recording
active_connections: Dict[str, WebSocket] = {}

# OAuth Routes
@app.get("/api/auth/login")
async def github_login():
    """Initiate GitHub OAuth login with comprehensive logging"""
    logger.info("🚀 Initiating GitHub OAuth login...")
    
    # Generate state parameter
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat()
    }
    
    logger.info(f"🔑 Generated OAuth state: {state[:8]}...")
    logger.info(f"🔑 OAuth state expires at: {oauth_states[state]['expires_at']}")
    log_sessions_state()
    
    # Generate authorization URL
    auth_url = github_oauth.generate_auth_url(state)
    
    logger.info(f"🔗 Redirecting to GitHub OAuth: {auth_url}")
    return {"auth_url": auth_url}

@app.get("/api/auth/github/callback")
async def github_callback(code: str, state: str, response: Response):
    """Handle GitHub OAuth callback with comprehensive logging"""
    logger.info("🔄 GitHub OAuth callback received")
    logger.info(f"🔄 Callback parameters: code={code[:8]}..., state={state[:8]}...")
    
    try:
        # Validate state parameter
        logger.info("🔍 Validating OAuth state...")
        if state not in oauth_states:
            logger.error(f"❌ Invalid OAuth state: {state[:8]}...")
            logger.error(f"❌ Available states: {[s[:8] + '...' for s in oauth_states.keys()]}")
            log_sessions_state()
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Check state expiration
        state_data = oauth_states[state]
        expires_at = datetime.fromisoformat(state_data["expires_at"])
        if datetime.now() > expires_at:
            logger.error(f"⏰ OAuth state expired: {state[:8]}... (expired at {expires_at})")
            del oauth_states[state]
            log_sessions_state()
            raise HTTPException(status_code=400, detail="OAuth state expired")
        
        logger.info(f"✅ OAuth state validated: {state[:8]}...")
        
        # Clean up used state
        del oauth_states[state]
        logger.info(f"🧹 Cleaned up used OAuth state: {state[:8]}...")
        
        # Exchange code for access token
        logger.info("🔄 Starting token exchange...")
        access_token = await github_oauth.exchange_code_for_token(code)
        logger.info(f"✅ Token exchange completed: {access_token[:8]}...")
        
        # Get user information
        logger.info("👤 Fetching user information...")
        user_data = await github_oauth.get_user_info(access_token)
        logger.info(f"✅ User information received: {user_data.get('login')}")
        
        # Create session
        logger.info("🆕 Creating user session...")
        session_id = create_session(user_data, access_token)
        logger.info(f"✅ Session created: {session_id[:8]}...")
        
        # Set session cookie
        logger.info("🍪 Setting session cookie...")
        response.set_cookie(
            key="qalia_session",
            value=session_id,
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info("✅ OAuth callback completed successfully!")
        logger.info(f"🔄 Redirecting to dashboard...")
        
        # Redirect to dashboard
        return RedirectResponse(url="/", status_code=302)
        
    except HTTPException as e:
        logger.error(f"❌ HTTP Exception in OAuth callback: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error in OAuth callback: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {e}")

@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user with detailed logging"""
    logger.info("🚪 Logout request received")
    
    session_id = request.cookies.get("qalia_session")
    if session_id:
        logger.info(f"🧹 Cleaning up session: {session_id[:8]}...")
        if session_id in sessions:
            del sessions[session_id]
            logger.info(f"✅ Session removed: {session_id[:8]}...")
        else:
            logger.warning(f"⚠️ Session not found for cleanup: {session_id[:8]}...")
    
    # Clear session cookie
    response.delete_cookie("qalia_session")
    logger.info("🍪 Session cookie cleared")
    
    log_sessions_state()
    
    return {"message": "Logged out successfully"}

@app.get("/api/auth/user")
async def get_user(request: Request):
    """Get current user information with detailed logging"""
    logger.info("🔍 API request: Get current user")
    
    user = get_current_user(request)
    if not user:
        logger.info("❌ User not authenticated")
        return {"authenticated": False, "user": None}
    
    logger.info(f"✅ User authenticated: {user.get('login')}")
    return {"authenticated": True, "user": user}


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
    sessions_list = [] # recording_sessions.get(repo_key, []) # This line is removed
    
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
    
    # recording_sessions[repo_key].append(recording_session) # This line is removed
    
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
        
        # List dist contents
        try:
            dist_contents = list(ui_dist_path.iterdir())
            logger.info(f"📁 Dist contents: {[f.name for f in dist_contents]}")
        except Exception as e:
            logger.error(f"❌ Error listing dist contents: {e}")
    
    uvicorn.run(
        "ui_only_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    ) 