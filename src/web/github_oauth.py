"""
GitHub OAuth Manager

Handles GitHub OAuth 2.0 authentication for web users.
This is separate from the GitHub App authentication used for automated operations.
"""

import os
import secrets
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import requests
from github import Github

logger = logging.getLogger(__name__)


class GitHubOAuth:
    """Manages GitHub OAuth 2.0 authentication for web users."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize GitHub OAuth manager.
        
        Args:
            client_id: GitHub OAuth App Client ID
            client_secret: GitHub OAuth App Client Secret  
            redirect_uri: OAuth callback URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://github.com"
        self.api_url = "https://api.github.com"
    
    def generate_auth_url(self, scopes: list = None) -> Tuple[str, str]:
        """
        Generate GitHub OAuth authorization URL.
        
        Args:
            scopes: List of OAuth scopes to request
            
        Returns:
            Tuple of (auth_url, state) where state is used for CSRF protection
        """
        if scopes is None:
            # Default scopes for Qalia UI
            scopes = [
                "user:email",      # Read user email addresses
                "read:user",       # Read user profile info
                "repo",            # Access public and private repositories
                "write:repo_hook"  # Create repository webhooks (if needed)
            ]
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "allow_signup": "false"  # Only existing GitHub users
        }
        
        auth_url = f"{self.base_url}/login/oauth/authorize?{urlencode(params)}"
        
        logger.info(f"Generated OAuth URL with scopes: {scopes}")
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str, state: str, expected_state: str) -> Optional[Dict[str, Any]]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            code: Authorization code from GitHub
            state: State parameter from GitHub
            expected_state: Expected state value for CSRF protection
            
        Returns:
            Token response dict or None if failed
        """
        # Verify state to prevent CSRF attacks
        if state != expected_state:
            logger.error("OAuth state mismatch - possible CSRF attack")
            return None
        
        # Exchange code for token
        token_url = f"{self.base_url}/login/oauth/access_token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Qalia-UI"
        }
        
        try:
            response = requests.post(token_url, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            if "error" in token_data:
                logger.error(f"OAuth token exchange error: {token_data}")
                return None
            
            if "access_token" not in token_data:
                logger.error("No access token in OAuth response")
                return None
            
            logger.info("OAuth token exchange successful")
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"OAuth token exchange failed: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from GitHub API.
        
        Args:
            access_token: GitHub OAuth access token
            
        Returns:
            User info dict or None if failed
        """
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json",
            "User-Agent": "Qalia-UI"
        }
        
        try:
            # Get user info
            user_response = requests.get(f"{self.api_url}/user", headers=headers, timeout=10)
            user_response.raise_for_status()
            user_data = user_response.json()
            
            # Get user emails
            emails_response = requests.get(f"{self.api_url}/user/emails", headers=headers, timeout=10)
            emails_response.raise_for_status()
            emails_data = emails_response.json()
            
            # Find primary email
            primary_email = None
            for email in emails_data:
                if email.get("primary"):
                    primary_email = email.get("email")
                    break
            
            # Combine user data
            user_info = {
                "id": user_data.get("id"),
                "login": user_data.get("login"),
                "name": user_data.get("name"),
                "email": primary_email or user_data.get("email"),
                "avatar_url": user_data.get("avatar_url"),
                "html_url": user_data.get("html_url"),
                "company": user_data.get("company"),
                "bio": user_data.get("bio"),
                "location": user_data.get("location"),
                "blog": user_data.get("blog"),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "created_at": user_data.get("created_at"),
                "updated_at": user_data.get("updated_at")
            }
            
            logger.info(f"Retrieved user info for: {user_info['login']}")
            return user_info
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    async def get_user_repositories(self, access_token: str, per_page: int = 100) -> list:
        """
        Get repositories accessible to the user.
        
        Args:
            access_token: GitHub OAuth access token
            per_page: Number of repositories per page
            
        Returns:
            List of repository dicts
        """
        try:
            # Use PyGitHub for easier repository management
            g = Github(access_token)
            user = g.get_user()
            
            repositories = []
            
            # Get user's own repositories
            for repo in user.get_repos(type="all", sort="updated", per_page=per_page):
                repo_data = {
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "default_branch": repo.default_branch,
                    "language": repo.language,
                    "languages_url": repo.languages_url,
                    "stargazers_count": repo.stargazers_count,
                    "watchers_count": repo.watchers_count,
                    "forks_count": repo.forks_count,
                    "size": repo.size,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                    "permissions": {
                        "admin": repo.permissions.admin,
                        "push": repo.permissions.push,
                        "pull": repo.permissions.pull
                    },
                    "owner": {
                        "login": repo.owner.login,
                        "avatar_url": repo.owner.avatar_url,
                        "html_url": repo.owner.html_url,
                        "type": repo.owner.type
                    }
                }
                repositories.append(repo_data)
            
            logger.info(f"Retrieved {len(repositories)} repositories for user")
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to get user repositories: {e}")
            return []
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid.
        
        Args:
            access_token: GitHub OAuth access token
            
        Returns:
            True if token is valid, False otherwise
        """
        headers = {
            "Authorization": f"token {access_token}",
            "User-Agent": "Qalia-UI"
        }
        
        try:
            response = requests.get(f"{self.api_url}/user", headers=headers, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False


def get_oauth_config() -> Dict[str, str]:
    """Get OAuth configuration from environment variables."""
    config = {
        "client_id": os.getenv("GITHUB_OAUTH_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_OAUTH_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
    }
    
    # Validate required config
    missing = [key for key, value in config.items() if not value]
    if missing:
        raise ValueError(f"Missing OAuth configuration: {', '.join(missing)}")
    
    return config


def create_oauth_manager() -> GitHubOAuth:
    """Create and configure GitHub OAuth manager."""
    config = get_oauth_config()
    return GitHubOAuth(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=config["redirect_uri"]
    ) 