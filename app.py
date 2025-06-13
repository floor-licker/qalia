from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import os
from typing import Dict, Any
import json
from github import Github
import jwt
import time
import asyncio
import tempfile
import shutil
from pathlib import Path
import logging

# Import QA AI functionality from the current directory
try:
    from main import run_complete_pipeline
    from scripts.run_exploration import run_exploration
    from generators import TestCaseGenerator
except ImportError as e:
    logging.error(f"Failed to import QA AI modules: {e}")
    # For development/testing, we'll handle this gracefully
    run_complete_pipeline = None

# Import configuration
from config import get_deployment_url, get_app_config, validate_config

app = FastAPI(title="QALIA GitHub App", description="AI-powered QA testing for your repositories")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub App configuration
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Read private key from PEM file
def get_private_key() -> str:
    """Read the private key from the PEM file."""
    try:
        with open("private-key.pem", "r") as key_file:
            return key_file.read()
    except FileNotFoundError:
        # Try alternative locations
        try:
            with open("app/private-key.pem", "r") as key_file:
                return key_file.read()
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="Private key file not found. Please ensure private-key.pem exists in the root directory."
            )

def verify_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify the webhook signature from GitHub."""
    if not GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification if no secret is set
    
    expected_signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

def get_github_client(installation_id: int) -> Github:
    """Get an authenticated GitHub client for the installation."""
    if not GITHUB_APP_ID:
        raise HTTPException(status_code=500, detail="GitHub App ID not configured")
    
    # Get private key
    private_key = get_private_key()
    
    # Generate JWT
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 600,  # 10 minutes
        "iss": GITHUB_APP_ID
    }
    
    jwt_token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )
    
    # Get installation access token
    g = Github(jwt=jwt_token)
    installation = g.get_installation(installation_id)
    token = installation.get_access_token()
    
    # Return client with installation token
    return Github(token.token)

async def run_qalia_analysis(repo_url: str, branch: str = "main") -> Dict[str, Any]:
    """Run QA AI analysis on a deployed application."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    if not run_complete_pipeline:
        raise HTTPException(status_code=500, detail="QA AI modules not available")
    
    # Use configuration module to determine deployment URL
    app_url = get_deployment_url(repo_url, branch)
    
    try:
        # Create temporary directory for results
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run QA AI analysis
            logger.info(f"Running QA AI analysis on {app_url}")
            
            exploration_options = {
                "headless": True,
                "max_depth": 3,
                "timeout": 300,
                "output_dir": temp_dir
            }
            
            generation_options = {
                "frameworks": ["playwright", "cypress", "jest"],
                "output_dir": temp_dir
            }
            
            results = await run_complete_pipeline(
                app_url, 
                exploration_options, 
                generation_options
            )
            
            # Process results
            analysis_summary = {
                "status": "completed",
                "app_url": app_url,
                "exploration_results": results.get("exploration_results", {}),
                "test_generation_results": results.get("test_generation_results", {}),
                "session_directory": results.get("session_directory"),
                "total_test_cases": 0,
                "issues_found": 0,
                "recommendations": []
            }
            
            # Extract key metrics
            exploration_summary = results.get("exploration_results", {}).get("exploration_summary", {})
            test_summary = results.get("test_generation_results", {}).get("summary", {})
            
            analysis_summary["total_test_cases"] = test_summary.get("generation_summary", {}).get("total_test_cases", 0)
            analysis_summary["issues_found"] = exploration_summary.get("errors_found", 0)
            
            return analysis_summary
            
    except Exception as e:
        logger.error(f"QA AI analysis failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "app_url": app_url
        }

async def create_check_run(g: Github, repo_name: str, commit_sha: str, analysis_results: Dict[str, Any]):
    """Create a GitHub check run with QA AI results."""
    repo = g.get_repo(repo_name)
    
    if analysis_results["status"] == "completed":
        conclusion = "success" if analysis_results["issues_found"] == 0 else "neutral"
        title = f"QA AI Analysis Complete - {analysis_results['total_test_cases']} tests generated"
        summary = f"""
## 🤖 QA AI Analysis Results

**Target Application:** `{analysis_results['app_url']}`

### 📊 Summary
- **Test Cases Generated:** {analysis_results['total_test_cases']}
- **Issues Found:** {analysis_results['issues_found']}
- **Status:** ✅ Analysis completed successfully

### 🧪 Generated Tests
QA AI has automatically generated comprehensive test suites for your application. The tests cover:
- User interface interactions
- Navigation flows
- Form submissions
- Error handling scenarios

### 🚀 Next Steps
1. Download the generated test files from the workflow artifacts
2. Integrate the tests into your CI/CD pipeline
3. Review and customize the tests as needed
        """
    else:
        conclusion = "failure"
        title = "QA AI Analysis Failed"
        summary = f"""
## ❌ QA AI Analysis Failed

**Target Application:** `{analysis_results.get('app_url', 'Unknown')}`
**Error:** {analysis_results.get('error', 'Unknown error occurred')}

Please check your application deployment and try again.
        """
    
    check_run = repo.create_check_run(
        name="QA AI Analysis",
        head_sha=commit_sha,
        status="completed",
        conclusion=conclusion,
        output={
            "title": title,
            "summary": summary
        }
    )
    
    return check_run

async def comment_on_pr(g: Github, repo_name: str, pr_number: int, analysis_results: Dict[str, Any]):
    """Comment on a pull request with QA AI results."""
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    if analysis_results["status"] == "completed":
        comment = f"""
## 🤖 QA AI Analysis Results

I've analyzed your application and generated **{analysis_results['total_test_cases']} test cases**!

### 📊 Summary
- **Target URL:** `{analysis_results['app_url']}`
- **Issues Found:** {analysis_results['issues_found']}
- **Status:** ✅ Analysis completed

### 🧪 What I Generated
- Comprehensive test suites covering your application
- User interaction tests
- Navigation flow tests
- Form validation tests
- Error handling scenarios

The generated tests are available in the workflow artifacts. You can download and integrate them into your testing pipeline.

---
*Powered by QA AI - Automated testing for modern web applications*
        """
    else:
        comment = f"""
## ❌ QA AI Analysis Failed

I encountered an issue while analyzing your application:

**Error:** {analysis_results.get('error', 'Unknown error')}
**Target URL:** `{analysis_results.get('app_url', 'Unknown')}`

Please check your application deployment and ensure it's accessible.

---
*Powered by QA AI*
        """
    
    pr.create_issue_comment(comment)

@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {"message": "QA AI GitHub App is running", "status": "healthy"}

@app.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    
    # Parse payload
    try:
        payload = json.loads(body.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Get event type
    event_type = request.headers.get("X-GitHub-Event")
    
    logger.info(f"Received {event_type} event")
    
    # Handle different event types
    if event_type == "pull_request":
        await handle_pull_request(payload)
    elif event_type == "push":
        await handle_push(payload)
    elif event_type == "installation":
        logger.info("App installation event received")
    else:
        logger.info(f"Unhandled event type: {event_type}")
    
    return {"status": "ok"}

async def handle_pull_request(payload: Dict[str, Any]):
    """Handle pull request events."""
    action = payload.get("action")
    
    # Only process opened and synchronize events
    if action not in ["opened", "synchronize"]:
        return
    
    # Get repository and PR information
    repo_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    commit_sha = payload["pull_request"]["head"]["sha"]
    branch = payload["pull_request"]["head"]["ref"]
    installation_id = payload["installation"]["id"]
    
    logger.info(f"Processing PR #{pr_number} in {repo_name}")
    
    # Get GitHub client
    g = get_github_client(installation_id)
    
    # Run QA AI analysis
    analysis_results = await run_qalia_analysis(repo_name, branch)
    
    # Get app configuration
    config = get_app_config()
    
    # Create check run if enabled
    if config["enable_check_runs"]:
        await create_check_run(g, repo_name, commit_sha, analysis_results)
    
    # Comment on PR if enabled
    if config["enable_pr_comments"]:
        await comment_on_pr(g, repo_name, pr_number, analysis_results)

async def handle_push(payload: Dict[str, Any]):
    """Handle push events."""
    # Only process pushes to main/master branch
    ref = payload.get("ref", "")
    if not ref.endswith("/main") and not ref.endswith("/master"):
        return
    
    # Get repository information
    repo_name = payload["repository"]["full_name"]
    commit_sha = payload["head_commit"]["id"]
    branch = ref.split("/")[-1]
    installation_id = payload["installation"]["id"]
    
    logger.info(f"Processing push to {branch} in {repo_name}")
    
    # Get GitHub client
    g = get_github_client(installation_id)
    
    # Run QA AI analysis
    analysis_results = await run_qalia_analysis(repo_name, branch)
    
    # Create check run
    await create_check_run(g, repo_name, commit_sha, analysis_results)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))) 