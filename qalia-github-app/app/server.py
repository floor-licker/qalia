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
import sys
import tempfile
import shutil
from pathlib import Path
import logging

# Add the parent directory to Python path to import QA AI modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import QA AI functionality
try:
    from main import run_complete_pipeline
    from scripts.run_exploration import run_exploration
    from generators import TestCaseGenerator
except ImportError as e:
    logging.error(f"Failed to import QA AI modules: {e}")
    # For development/testing, we'll handle this gracefully
    run_complete_pipeline = None

# Import local configuration
from config import get_deployment_url, get_app_config, validate_config

app = FastAPI(title="QALIA GitHub App")

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
        with open("app/private-key.pem", "r") as key_file:
            return key_file.read()
    except FileNotFoundError:
        # Try alternative locations
        try:
            with open("private-key.pem", "r") as key_file:
                return key_file.read()
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="Private key file not found. Please ensure private-key.pem exists."
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

**Error:** {analysis_results.get('error', 'Unknown error')}

**Target Application:** `{analysis_results.get('app_url', 'Unknown')}`

Please check your application deployment and ensure it's accessible for analysis.
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
    """Add a comment to the PR with QA AI results."""
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    if analysis_results["status"] == "completed":
        comment_body = f"""
## 🤖 QA AI Analysis Results

I've automatically analyzed your application and generated comprehensive test suites!

### 📊 Summary
- **Target Application:** `{analysis_results['app_url']}`
- **Test Cases Generated:** **{analysis_results['total_test_cases']}**
- **Issues Found:** {analysis_results['issues_found']}

### 🧪 What's Generated
QA AI has created test files for multiple frameworks:
- **Playwright** - End-to-end browser tests
- **Cypress** - Modern web testing
- **Jest** - Unit and integration tests

### 🚀 How to Use
1. The generated tests are available in the workflow artifacts
2. Download and integrate them into your testing pipeline
3. Run the tests as part of your CI/CD process

### 💡 Benefits
- **Comprehensive Coverage** - Tests generated from actual user interactions
- **Multiple Frameworks** - Choose the testing framework that fits your stack
- **Ready to Run** - Tests are pre-configured and executable

*This analysis was performed automatically by QA AI. The tests are generated based on autonomous exploration of your deployed application.*
        """
    else:
        comment_body = f"""
## ❌ QA AI Analysis Failed

I encountered an issue while analyzing your application:

**Error:** {analysis_results.get('error', 'Unknown error')}
**Target URL:** `{analysis_results.get('app_url', 'Unknown')}`

### 🔧 Troubleshooting
- Ensure your application is deployed and accessible
- Check that the deployment URL is correct
- Verify the application is fully loaded before analysis

*This is an automated comment from QA AI. Please check your deployment status and try again.*
        """
    
    pr.create_issue_comment(comment_body)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "QA AI GitHub App is running", "version": "1.0.0"}

@app.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    # Get the signature from headers
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="No signature provided")
    
    # Get the event type
    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(status_code=400, detail="No event type provided")
    
    # Get the request body
    body = await request.body()
    
    # Verify the signature
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse the payload
    payload = json.loads(body)
    
    # Handle different event types
    try:
        if event_type == "pull_request":
            await handle_pull_request(payload)
        elif event_type == "push":
            await handle_push(payload)
        else:
            logger.info(f"Ignoring event type: {event_type}")
    except Exception as e:
        logger.error(f"Error handling {event_type} event: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
    
    return JSONResponse({"status": "success"})

async def handle_pull_request(payload: Dict[str, Any]):
    """Handle pull request events."""
    action = payload.get("action")
    if action not in ["opened", "synchronize"]:
        logger.info(f"Ignoring PR action: {action}")
        return
    
    pr = payload.get("pull_request", {})
    repository = payload.get("repository", {})
    installation_id = payload.get("installation", {}).get("id")
    
    if not installation_id:
        raise HTTPException(status_code=400, detail="No installation ID provided")
    
    repo_name = repository.get("full_name")
    pr_number = pr.get("number")
    commit_sha = pr.get("head", {}).get("sha")
    
    logger.info(f"Processing PR #{pr_number} in {repo_name}")
    
    # Get authenticated GitHub client
    g = get_github_client(installation_id)
    
    # Create initial check run
    repo = g.get_repo(repo_name)
    check_run = repo.create_check_run(
        name="QA AI Analysis",
        head_sha=commit_sha,
        status="in_progress",
        output={
            "title": "Running QA AI Analysis...",
            "summary": "🤖 QA AI is analyzing your application and generating test cases. This may take a few minutes."
        }
    )
    
    try:
        # Run QA AI analysis
        analysis_results = await run_qalia_analysis(repo_name)
        
        # Update check run with results
        await create_check_run(g, repo_name, commit_sha, analysis_results)
        
        # Comment on PR
        await comment_on_pr(g, repo_name, pr_number, analysis_results)
        
        logger.info(f"QA AI analysis completed for PR #{pr_number}")
        
    except Exception as e:
        # Update check run with failure
        check_run.edit(
            status="completed",
            conclusion="failure",
            output={
                "title": "QA AI Analysis Failed",
                "summary": f"❌ Analysis failed: {str(e)}"
            }
        )
        logger.error(f"QA AI analysis failed for PR #{pr_number}: {e}")

async def handle_push(payload: Dict[str, Any]):
    """Handle push events to main branch."""
    ref = payload.get("ref")
    if ref != "refs/heads/main":
        logger.info(f"Ignoring push to {ref}")
        return
    
    repository = payload.get("repository", {})
    installation_id = payload.get("installation", {}).get("id")
    
    if not installation_id:
        raise HTTPException(status_code=400, detail="No installation ID provided")
    
    repo_name = repository.get("full_name")
    commit_sha = payload.get("after")
    
    logger.info(f"Processing push to main in {repo_name}")
    
    # Get authenticated GitHub client
    g = get_github_client(installation_id)
    
    try:
        # Run QA AI analysis
        analysis_results = await run_qalia_analysis(repo_name)
        
        # Create check run with results
        await create_check_run(g, repo_name, commit_sha, analysis_results)
        
        logger.info(f"QA AI analysis completed for push to {repo_name}")
        
    except Exception as e:
        logger.error(f"QA AI analysis failed for push to {repo_name}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 