"""
Session Manager

Handles user session management for the Qalia web UI.
Stores authentication state, user info, and session data.
"""

import time
import secrets
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Represents a user session."""
    session_id: str
    user_id: str
    user_login: str
    user_name: str
    user_email: str
    user_avatar_url: str
    access_token: str
    token_type: str
    scope: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if the session is active (not expired and recently used)."""
        if self.is_expired():
            return False
        
        # Consider session inactive if not used in last 24 hours
        inactive_threshold = datetime.utcnow() - timedelta(hours=24)
        return self.last_activity > inactive_threshold
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary (excluding sensitive data for client)."""
        return {
            "session_id": self.session_id,
            "user": {
                "id": self.user_id,
                "login": self.user_login,
                "name": self.user_name,
                "email": self.user_email,
                "avatar_url": self.user_avatar_url
            },
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active(),
            "scope": self.scope
        }


class SessionManager:
    """Manages user sessions for the web UI."""
    
    def __init__(self, session_duration_hours: int = 24):
        """
        Initialize session manager.
        
        Args:
            session_duration_hours: How long sessions should last
        """
        self.session_duration_hours = session_duration_hours
        self.sessions: Dict[str, UserSession] = {}
        self.oauth_states: Dict[str, Dict[str, Any]] = {}  # For OAuth CSRF protection
        
        # Start cleanup task
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # Cleanup every hour
    
    def generate_oauth_state(self) -> str:
        """Generate OAuth state for CSRF protection."""
        state = secrets.token_urlsafe(32)
        self.oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)  # States expire in 10 minutes
        }
        
        # Cleanup old states
        self._cleanup_oauth_states()
        
        return state
    
    def validate_oauth_state(self, state: str) -> bool:
        """Validate OAuth state."""
        if state not in self.oauth_states:
            return False
        
        state_data = self.oauth_states[state]
        if datetime.utcnow() > state_data["expires_at"]:
            # State expired
            del self.oauth_states[state]
            return False
        
        # Remove state after validation (one-time use)
        del self.oauth_states[state]
        return True
    
    def create_session(
        self, 
        user_info: Dict[str, Any], 
        token_data: Dict[str, Any]
    ) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_info: User information from GitHub API
            token_data: Token data from OAuth exchange
            
        Returns:
            New UserSession object
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.session_duration_hours)
        
        session = UserSession(
            session_id=session_id,
            user_id=str(user_info["id"]),
            user_login=user_info["login"],
            user_name=user_info.get("name") or user_info["login"],
            user_email=user_info.get("email", ""),
            user_avatar_url=user_info.get("avatar_url", ""),
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "bearer"),
            scope=token_data.get("scope", ""),
            created_at=now,
            expires_at=expires_at,
            last_activity=now
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Created session for user: {user_info['login']} (expires: {expires_at})")
        
        # Cleanup old sessions
        self._cleanup_sessions()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession if found and active, None otherwise
        """
        if not session_id or session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        if session.is_expired():
            # Session expired, remove it
            del self.sessions[session_id]
            logger.info(f"Removed expired session for user: {session.user_login}")
            return None
        
        # Update last activity
        session.update_activity()
        
        return session
    
    def get_session_by_user_id(self, user_id: str) -> Optional[UserSession]:
        """
        Get active session for a user.
        
        Args:
            user_id: GitHub user ID
            
        Returns:
            UserSession if found and active, None otherwise
        """
        for session in list(self.sessions.values()):
            if session.user_id == user_id and session.is_active():
                session.update_activity()
                return session
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session (logout).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            del self.sessions[session_id]
            logger.info(f"Deleted session for user: {session.user_login}")
            return True
        
        return False
    
    def list_active_sessions(self) -> list:
        """
        List all active sessions.
        
        Returns:
            List of active UserSession objects
        """
        active_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            if session.is_active():
                session.update_activity()
                active_sessions.append(session)
            elif session.is_expired():
                # Remove expired session
                del self.sessions[session_id]
        
        return active_sessions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        active_sessions = self.list_active_sessions()
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "oauth_states": len(self.oauth_states),
            "last_cleanup": self._last_cleanup,
            "session_duration_hours": self.session_duration_hours
        }
    
    def _cleanup_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        
        # Only cleanup if it's been more than the cleanup interval
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            session = self.sessions[session_id]
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session for user: {session.user_login}")
        
        self._last_cleanup = current_time
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def _cleanup_oauth_states(self):
        """Remove expired OAuth states."""
        now = datetime.utcnow()
        expired_states = []
        
        for state, data in self.oauth_states.items():
            if now > data["expires_at"]:
                expired_states.append(state)
        
        for state in expired_states:
            del self.oauth_states[state]
        
        if expired_states:
            logger.debug(f"Cleaned up {len(expired_states)} expired OAuth states")


# Global session manager instance
session_manager = SessionManager() 