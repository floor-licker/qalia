"""
UI Server Module

FastAPI routes and handlers for serving the React UI and handling
the embedded browser recording interface.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends, Cookie, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.web.github_oauth import create_oauth_manager, GitHubOAuth
from src.web.session_manager import session_manager, UserSession

logger = logging.getLogger(__name__)


class UIServer:
    """Handles UI-related routes and WebSocket connections for the embedded recorder."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Initialize OAuth manager (with error handling for missing config)
        try:
            self.oauth_manager = create_oauth_manager()
        except ValueError as e:
            logger.warning(f"OAuth not configured: {e}")
            self.oauth_manager = None
        
        self.setup_ui_routes()
        self.setup_cors()
    
    async def get_current_user(self, qalia_session: Optional[str] = Cookie(None)) -> Optional[UserSession]:
        """Dependency to get current authenticated user."""
        if not qalia_session:
            return None
        
        return session_manager.get_session(qalia_session)
    
    async def require_auth(self, qalia_session: Optional[str] = Cookie(None)) -> UserSession:
        """Dependency that requires authentication."""
        current_user = await self.get_current_user(qalia_session)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return current_user
    
    def setup_cors(self):
        """Configure CORS for development with Vite dev server."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],  # Vite dev server
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_ui_routes(self):
        """Set up routes for serving the UI and handling recording sessions."""
        
        # Development route - proxy to Vite dev server
        @self.app.get("/ui", response_class=HTMLResponse)
        async def serve_ui_dev():
            """Serve UI during development (redirects to Vite dev server)."""
            # In development, redirect to Vite dev server
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
        
        # Production route - serve built React app
        ui_dist_path = Path(__file__).parent.parent.parent / "ui" / "dist"
        if ui_dist_path.exists():
            # Mount static files for production
            self.app.mount("/ui/assets", StaticFiles(directory=ui_dist_path / "assets"), name="ui-assets")
            
            @self.app.get("/ui/{path:path}")
            async def serve_ui_prod(path: str = ""):
                """Serve built React app in production."""
                if path and (ui_dist_path / path).exists():
                    return FileResponse(ui_dist_path / path)
                # Fallback to index.html for SPA routing
                return FileResponse(ui_dist_path / "index.html")
        
        # OAuth Authentication Routes
        @self.app.get("/api/auth/login")
        async def github_login():
            """Initiate GitHub OAuth login."""
            if not self.oauth_manager:
                raise HTTPException(status_code=500, detail="OAuth not configured")
            
            # Generate OAuth state for CSRF protection
            state = session_manager.generate_oauth_state()
            
            # Generate GitHub OAuth URL
            auth_url, _ = self.oauth_manager.generate_auth_url()
            
            # Add our state to the URL
            auth_url += f"&state={state}"
            
            return {"auth_url": auth_url}
        
        @self.app.get("/api/auth/callback")
        async def github_callback(code: str, state: str, response: Response):
            """Handle GitHub OAuth callback."""
            if not self.oauth_manager:
                raise HTTPException(status_code=500, detail="OAuth not configured")
            
            # Validate state to prevent CSRF
            if not session_manager.validate_oauth_state(state):
                raise HTTPException(status_code=400, detail="Invalid or expired state")
            
            # Exchange code for token
            token_data = await self.oauth_manager.exchange_code_for_token(code, state, state)
            if not token_data:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            # Get user info
            user_info = await self.oauth_manager.get_user_info(token_data["access_token"])
            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            # Create session
            session = session_manager.create_session(user_info, token_data)
            
            # Set session cookie
            response.set_cookie(
                key="qalia_session",
                value=session.session_id,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            
            return RedirectResponse(url="/ui", status_code=302)
        
        @self.app.post("/api/auth/logout")
        async def logout(response: Response, qalia_session: Optional[str] = Cookie(None)):
            """Logout user."""
            if qalia_session:
                session_manager.delete_session(qalia_session)
            
            # Clear session cookie
            response.delete_cookie(key="qalia_session")
            
            return {"message": "Logged out successfully"}
        
        @self.app.get("/api/auth/user")
        async def get_current_user_info(qalia_session: Optional[str] = Cookie(None)):
            """Get current authenticated user info."""
            current_user = await self.get_current_user(qalia_session)
            
            if not current_user:
                return {"user": None, "authenticated": False}
            
            return {
                "user": current_user.to_dict()["user"],
                "authenticated": True,
                "session": {
                    "created_at": current_user.created_at.isoformat(),
                    "expires_at": current_user.expires_at.isoformat(),
                    "scope": current_user.scope
                }
            }
        
        # Repository and Session Management Routes (protected)
        @self.app.get("/api/repos")
        async def list_repositories(qalia_session: Optional[str] = Cookie(None)):
            """List repositories accessible to the current user."""
            current_user = await self.require_auth(qalia_session)
            
            if not self.oauth_manager:
                raise HTTPException(status_code=500, detail="OAuth not configured")
            
            # Get user repositories using their access token
            repositories = await self.oauth_manager.get_user_repositories(current_user.access_token)
            
            return {"repositories": repositories}
        
        @self.app.get("/api/repos/{owner}/{repo}/sessions")
        async def list_recording_sessions(owner: str, repo: str, qalia_session: Optional[str] = Cookie(None)):
            """List recording sessions for a repository."""
            current_user = await self.require_auth(qalia_session)
            
            # TODO: Implement session storage integration with user context
            # For now, return empty list
            return {"sessions": [], "repository": f"{owner}/{repo}", "user": current_user.user_login}
        
        @self.app.post("/api/repos/{owner}/{repo}/sessions")
        async def create_recording_session(owner: str, repo: str, request: Request, qalia_session: Optional[str] = Cookie(None)):
            """Create a new recording session."""
            current_user = await self.require_auth(qalia_session)
            
            data = await request.json()
            
            # TODO: Implement session creation with user context
            session_id = f"session_{current_user.user_id}_{owner}_{repo}_{int(time.time())}"
            
            return {
                "session_id": session_id, 
                "status": "created",
                "repository": f"{owner}/{repo}",
                "user": current_user.user_login,
                "data": data
            }
        
        @self.app.get("/api/repos/{owner}/{repo}/tests")
        async def list_test_cases(owner: str, repo: str, qalia_session: Optional[str] = Cookie(None)):
            """List test cases for a repository."""
            current_user = await self.require_auth(qalia_session)
            
            # TODO: Implement test case storage integration with user context
            return {"tests": [], "repository": f"{owner}/{repo}", "user": current_user.user_login}
        
        # WebSocket endpoint for real-time recording
        @self.app.websocket("/ws/recording/{session_id}")
        async def recording_websocket(websocket: WebSocket, session_id: str):
            """Handle real-time recording WebSocket connections."""
            await self.handle_recording_websocket(websocket, session_id)
    
    async def handle_recording_websocket(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket connection for recording sessions."""
        await websocket.accept()
        
        # Store the connection
        self.active_connections[session_id] = websocket
        
        try:
            logger.info(f"Recording WebSocket connected for session: {session_id}")
            
            while True:
                # Receive messages from the client
                data = await websocket.receive_json()
                
                # Handle different message types
                await self.handle_recording_message(session_id, data)
                
        except WebSocketDisconnect:
            logger.info(f"Recording WebSocket disconnected for session: {session_id}")
            # Remove the connection
            if session_id in self.active_connections:
                del self.active_connections[session_id]
        except Exception as e:
            logger.error(f"Error in recording WebSocket for session {session_id}: {e}")
            if session_id in self.active_connections:
                del self.active_connections[session_id]
    
    async def handle_recording_message(self, session_id: str, message: Dict[str, Any]):
        """Process recording messages from the client."""
        message_type = message.get("type")
        
        if message_type == "action_recorded":
            # Handle recorded action
            action_data = message.get("action", {})
            logger.info(f"Action recorded in session {session_id}: {action_data}")
            
            # TODO: Store action in session
            # TODO: Process action through existing ActionExecutor
            
            # Echo back confirmation
            await self.send_to_session(session_id, {
                "type": "action_confirmed",
                "action_id": action_data.get("id"),
                "timestamp": action_data.get("timestamp")
            })
            
        elif message_type == "recording_started":
            logger.info(f"Recording started for session: {session_id}")
            # TODO: Initialize recording session
            
        elif message_type == "recording_stopped":
            logger.info(f"Recording stopped for session: {session_id}")
            # TODO: Finalize recording session
    
    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send a message to a specific recording session."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")
                # Remove broken connection
                if session_id in self.active_connections:
                    del self.active_connections[session_id]
    
    async def broadcast_to_all_sessions(self, message: Dict[str, Any]):
        """Broadcast a message to all active recording sessions."""
        disconnected_sessions = []
        
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to session {session_id}: {e}")
                disconnected_sessions.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            del self.active_connections[session_id]


def setup_ui_server(app: FastAPI) -> UIServer:
    """Initialize and configure the UI server."""
    ui_server = UIServer(app)
    logger.info("UI Server initialized with routes and WebSocket support")
    return ui_server 