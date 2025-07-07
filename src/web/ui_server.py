"""
UI Server Module

FastAPI routes and handlers for serving the React UI and handling
the embedded browser recording interface.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


class UIServer:
    """Handles UI-related routes and WebSocket connections for the embedded recorder."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.active_connections: Dict[str, WebSocket] = {}
        self.setup_ui_routes()
        self.setup_cors()
    
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
        
        # API Routes for UI functionality
        @self.app.get("/api/auth/user")
        async def get_current_user():
            """Get current authenticated user info."""
            # TODO: Implement GitHub OAuth user info
            return {"user": None, "authenticated": False}
        
        @self.app.get("/api/repos")
        async def list_repositories():
            """List repositories accessible to the current user."""
            # TODO: Implement GitHub API integration
            return {"repositories": []}
        
        @self.app.get("/api/repos/{owner}/{repo}/sessions")
        async def list_recording_sessions(owner: str, repo: str):
            """List recording sessions for a repository."""
            # TODO: Implement session storage integration
            return {"sessions": []}
        
        @self.app.post("/api/repos/{owner}/{repo}/sessions")
        async def create_recording_session(owner: str, repo: str, request: Request):
            """Create a new recording session."""
            data = await request.json()
            # TODO: Implement session creation
            return {"session_id": "temp-session-id", "status": "created"}
        
        @self.app.get("/api/repos/{owner}/{repo}/tests")
        async def list_test_cases(owner: str, repo: str):
            """List test cases for a repository."""
            # TODO: Implement test case storage integration
            return {"tests": []}
        
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