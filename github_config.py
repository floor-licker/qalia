"""
Configuration module for QA AI GitHub App

This module helps determine the deployment URL for applications
based on repository information and common hosting patterns.
"""

import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_deployment_url(repo_name: str, branch: str = "main") -> str:
    """
    Determine the deployment URL for a repository.
    
    This function tries multiple strategies to determine where an app is deployed:
    1. Environment variable override
    2. Repository-specific configuration
    3. Common hosting platform patterns
    
    Args:
        repo_name: Full repository name (e.g., "mycompany/myapp")
        branch: Git branch name
        
    Returns:
        Deployment URL string
    """
    
    # Strategy 1: Check for explicit URL override
    env_key = f"DEPLOY_URL_{repo_name.replace('/', '_').replace('-', '_').upper()}"
    explicit_url = os.getenv(env_key)
    if explicit_url:
        logger.info(f"Using explicit deployment URL from {env_key}: {explicit_url}")
        return explicit_url
    
    # Strategy 2: Check for generic deployment URL
    generic_url = os.getenv("DEFAULT_DEPLOY_URL")
    if generic_url:
        # Replace placeholders
        url = generic_url.replace("{repo}", repo_name.split("/")[-1])
        url = url.replace("{org}", repo_name.split("/")[0])
        url = url.replace("{branch}", branch)
        logger.info(f"Using generic deployment URL pattern: {url}")
        return url
    
    # Strategy 3: No fallback patterns - require explicit configuration
    app_name = repo_name.split("/")[-1]
    org_name = repo_name.split("/")[0]
    
    # No more fallback patterns - configuration must be explicit
    raise ValueError(
        f"No deployment URL configured for repository '{repo_name}'. "
        f"Please set either DEPLOY_URL_{repo_name.replace('/', '_').replace('-', '_').upper()} "
        f"or DEFAULT_DEPLOY_URL environment variable, or use qalia.yml configuration."
    )

def get_app_config() -> Dict[str, Any]:
    """Get application configuration from environment variables."""
    return {
        "github_app_id": os.getenv("GITHUB_APP_ID"),
        "github_webhook_secret": os.getenv("GITHUB_WEBHOOK_SECRET"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "max_analysis_timeout": int(os.getenv("MAX_ANALYSIS_TIMEOUT", "600")),
        "max_exploration_depth": int(os.getenv("MAX_EXPLORATION_DEPTH", "3")),
        "default_frameworks": os.getenv("DEFAULT_FRAMEWORKS", "playwright,cypress,jest").split(","),
        "enable_pr_comments": os.getenv("ENABLE_PR_COMMENTS", "true").lower() == "true",
        "enable_check_runs": os.getenv("ENABLE_CHECK_RUNS", "true").lower() == "true",
    }

def validate_config() -> bool:
    """Validate that required configuration is present."""
    config = get_app_config()
    required_fields = ["github_app_id", "github_webhook_secret", "openai_api_key"]
    
    missing_fields = [field for field in required_fields if not config[field]]
    
    if missing_fields:
        logger.error(f"Missing required configuration: {', '.join(missing_fields)}")
        return False
    
    return True 