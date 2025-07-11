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
        logger.info(f"📝 Generated state: {state[:8]}... (expires in 10 minutes)")
        logger.info(f"📝 Stored {len(oauth_states)} states in memory")
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str):
        """Exchange authorization code for access token"""
        logger.info("🔄 Making token exchange request to GitHub...")
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
            
            logger.info(f"📝 Token exchange response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Token exchange failed with status {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = response.json()
            logger.info(f"📝 Token exchange response: {list(token_data.keys())}")
            
            if "error" in token_data:
                logger.error(f"❌ OAuth error in token response: {token_data.get('error_description', 'Unknown error')}")
                raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth error"))
            
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error("❌ No access token in response")
                logger.error(f"❌ Response data: {token_data}")
                raise HTTPException(status_code=400, detail="No access token received")
            
            logger.info("✅ Access token received successfully")
            return access_token
    
    async def get_user_info(self, access_token: str):
        """Get user information from GitHub API"""
        logger.info("🔄 Fetching user info from GitHub API...")
        async with httpx.AsyncClient() as client:
            # Get user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            logger.info(f"📝 User info response status: {user_response.status_code}")
            
            if user_response.status_code != 200:
                logger.error(f"❌ Failed to get user info: {user_response.status_code}")
                logger.error(f"❌ Response: {user_response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            user_data = user_response.json()
            logger.info(f"📝 User info received: {user_data.get('login', 'unknown')} (ID: {user_data.get('id', 'unknown')})")
            
            # Get user emails
            logger.info("🔄 Fetching user emails...")
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            logger.info(f"📝 Emails response status: {emails_response.status_code}")
            
            emails = []
            if emails_response.status_code == 200:
                emails = emails_response.json()
                logger.info(f"📝 Found {len(emails)} email addresses")
                # Find primary email
                primary_email = next((email["email"] for email in emails if email["primary"]), None)
                if primary_email:
                    user_data["email"] = primary_email
                    logger.info(f"📝 Primary email set: {primary_email}")
                else:
                    logger.info("📝 No primary email found")
            else:
                logger.warning(f"⚠️  Failed to fetch emails: {emails_response.status_code}")
            
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
    
    logger.info(f"📝 Session created for user: {user_data.get('login', 'unknown')}")
    logger.info(f"📝 Session ID: {session_id[:8]}...")
    logger.info(f"📝 Total active sessions: {len(sessions)}")
    
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
        logger.info("🔐 Initiating GitHub OAuth login...")
        auth_url, state = github_oauth.generate_auth_url()
        logger.info(f"✅ Generated auth URL with state: {state[:8]}...")
        logger.info(f"🔗 Redirecting to: {auth_url}")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"❌ Failed to generate auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")

@app.get("/api/auth/github/callback")
async def github_callback(code: str, state: str, response: Response):
    """Handle GitHub OAuth callback"""
    try:
        logger.info("🔄 GitHub OAuth callback received")
        logger.info(f"📝 Code: {code[:10]}...")
        logger.info(f"📝 State: {state[:8]}...")
        logger.info(f"📝 Available states: {list(oauth_states.keys())}")
        
        # Validate state
        if state not in oauth_states:
            logger.error(f"❌ Invalid state parameter: {state[:8]}...")
            logger.error(f"❌ Expected one of: {list(oauth_states.keys())}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        logger.info("✅ State validation passed")
        
        # Check if state is expired
        state_data = oauth_states[state]
        if datetime.utcnow() > state_data["expires_at"]:
            logger.error(f"❌ State parameter expired: {state[:8]}...")
            del oauth_states[state]
            raise HTTPException(status_code=400, detail="State parameter expired")
        
        logger.info("✅ State expiration check passed")
        
        # Remove state (one-time use)
        del oauth_states[state]
        logger.info("✅ State consumed successfully")
        
        # Exchange code for access token
        logger.info("🔄 Exchanging code for access token...")
        access_token = await github_oauth.exchange_code_for_token(code)
        logger.info(f"✅ Access token obtained: {access_token[:10]}...")
        
        # Get user information
        logger.info("🔄 Fetching user information...")
        user_data = await github_oauth.get_user_info(access_token)
        logger.info(f"✅ User info obtained: {user_data.get('login', 'unknown')} ({user_data.get('email', 'no email')})")
        
        # Create session
        logger.info("🔄 Creating session...")
        session_id = create_session(user_data, access_token)
        logger.info(f"✅ Session created: {session_id[:8]}...")
        
        # Set secure cookie
        logger.info("🔄 Setting session cookie...")
        response.set_cookie(
            key="qalia_session",
            value=session_id,
            max_age=24 * 60 * 60,
            httponly=True,
            secure=False,  # Set to False for HTTP (True for HTTPS)
            samesite="lax"
        )
        logger.info("✅ Session cookie set")
        
        # Redirect to frontend
        redirect_url = "http://157.245.241.244"
        logger.info(f"🔄 Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException as e:
        logger.error(f"❌ OAuth callback HTTP error: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
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
    logger.info("🔍 Checking user authentication...")
    logger.info(f"📝 Session cookie: {qalia_session[:8] if qalia_session else 'None'}...")
    logger.info(f"📝 Active sessions: {len(sessions)}")
    
    session = get_session(qalia_session)
    
    if not session:
        logger.info("❌ No valid session found")
        return {"user": None, "authenticated": False}
    
    logger.info(f"✅ Valid session found for user: {session['user'].get('login', 'unknown')}")
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