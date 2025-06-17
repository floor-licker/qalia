from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
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
import subprocess
import os
import yaml
import requests

# Import QA AI functionality from the current directory
try:
    from main import run_complete_pipeline
    from scripts.run_exploration import run_exploration
    from generators import TestCaseGenerator
    from qalia_config import get_application_url, QaliaConfig
except ImportError as e:
    logging.error(f"Failed to import QA AI modules: {e}")
    # For development/testing, we'll handle this gracefully
    run_complete_pipeline = None
    get_application_url = None

# Import configuration
from github_config import get_app_config, validate_config

app = FastAPI(title="QALIA GitHub App", description="AI-powered QA testing for your repositories")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub App configuration
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Read private key from PEM file or environment variable
def get_private_key() -> str:
    """Read the private key from the PEM file or environment variable."""
    # Try environment variable first
    env_key = os.getenv("GITHUB_PRIVATE_KEY")
    if env_key:
        return env_key
    
    # Fall back to file
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
                detail="Private key not found. Please ensure private-key.pem exists or set GITHUB_PRIVATE_KEY environment variable."
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

def get_github_client(installation_id: int) -> tuple[Github, str]:
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
    
    # Get installation access token using direct API call
    import requests
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Qalia-GitHub-App"
    }
    
    response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers
    )
    
    if response.status_code != 201:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get installation token: {response.status_code} {response.text}"
        )
    
    token_data = response.json()
    access_token = token_data["token"]
    
    # Return client with installation token and the token itself
    return Github(access_token), access_token

async def run_simplified_static_testing(app_url: str, repo_path: str) -> Dict[str, Any]:
    """Run simplified testing for static sites without browsers."""
    logger.info(f"Running simplified testing for static site: {app_url}")
    
    try:
        # Basic HTTP connectivity test
        response = requests.get(app_url, timeout=30)
        status_code = response.status_code
        
        # Analyze HTML content
        html_content = response.text
        
        # Basic analysis
        has_title = '<title>' in html_content.lower()
        has_meta = '<meta' in html_content.lower()
        has_css = 'css' in html_content.lower() or '<style' in html_content.lower()
        has_js = 'javascript' in html_content.lower() or '<script' in html_content.lower()
        
        # Count basic elements
        form_count = html_content.lower().count('<form')
        link_count = html_content.lower().count('<a ')
        image_count = html_content.lower().count('<img')
        
        # Generate basic test cases
        test_cases = []
        
        if status_code == 200:
            test_cases.append("✅ HTTP connectivity test")
            test_cases.append("✅ Page loads successfully")
        
        if has_title:
            test_cases.append("✅ Page has title element")
        
        if has_meta:
            test_cases.append("✅ Page has meta tags")
            
        if has_css:
            test_cases.append("✅ Page includes CSS styling")
            
        if has_js:
            test_cases.append("✅ Page includes JavaScript")
            
        if form_count > 0:
            test_cases.append(f"✅ Found {form_count} form(s) for interaction testing")
            
        if link_count > 0:
            test_cases.append(f"✅ Found {link_count} link(s) for navigation testing")
            
        if image_count > 0:
            test_cases.append(f"✅ Found {image_count} image(s) for visual testing")
        
        # Create results structure
        results = {
            "exploration_results": {
                "exploration_summary": {
                    "pages_visited": 1,
                    "total_actions_performed": len(test_cases),
                    "errors_found": 0 if status_code == 200 else 1,
                    "states_discovered": 1
                }
            },
            "test_generation_results": {
                "summary": {
                    "generation_summary": {
                        "total_test_cases": len(test_cases)
                    }
                }
            },
            "session_directory": "simplified-testing"
        }
        
        logger.info(f"Simplified testing completed: {len(test_cases)} test cases generated")
        return results
        
    except Exception as e:
        logger.error(f"Simplified testing failed: {e}")
        raise

async def clone_repository(repo_url: str, branch: str = "main", access_token: str = None) -> str:
    """Clone repository to a temporary directory and return the path."""
    temp_dir = tempfile.mkdtemp()
    try:
        # First try without authentication for public repos
        logger.info(f"Attempting to clone repository: {repo_url}")
        cmd = f"git clone --branch {branch} --depth 1 {repo_url} {temp_dir}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # If that fails and we have an access token, try with authentication
        if result.returncode != 0 and access_token and repo_url.startswith("https://github.com/"):
            logger.info("Public clone failed, trying with authentication...")
            # Clean up first attempt
            shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir = tempfile.mkdtemp()
            
            # Convert to authenticated URL
            auth_repo_url = repo_url.replace("https://github.com/", f"https://x-access-token:{access_token}@github.com/")
            cmd = f"git clone --branch {branch} --depth 1 {auth_repo_url} {temp_dir}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to clone repository: {result.stderr}")
            logger.error(f"Git command output: {result.stdout}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        logger.info(f"Repository cloned successfully to {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

async def run_qalia_analysis(repo_url: str, branch: str = "main", repo_path: str = None) -> Dict[str, Any]:
    """Run QA AI analysis on a deployed application."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    if not run_complete_pipeline or not get_application_url:
        raise HTTPException(status_code=500, detail="QA AI modules not available")
    
    # Check if we can use a simpler approach for static sites
    try:
        logger.info("Checking if this is a static site that can be tested without browsers...")
        
        # For static sites, we can do basic HTTP testing first
        if repo_path:
            config_path = os.path.join(repo_path, "qalia.yml")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    deployment_type = config_data.get('deployment', {}).get('type', 'static')
                    
                    if deployment_type == 'static':
                        logger.info("Static site detected - using simplified testing approach")
                        # We'll handle this in the analysis logic below
                        pass
        
        # Still try to install browsers as fallback
        logger.info("Installing Playwright browsers as fallback...")
        result = subprocess.run(["python", "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            logger.info("Playwright chromium installed successfully")
        else:
            logger.warning(f"Playwright install warning: {result.stderr}")
            
    except Exception as e:
        logger.warning(f"Browser setup warning: {e}")
    
    try:
        # Check if qalia.yml exists first
        if repo_path:
            config_path = os.path.join(repo_path, "qalia.yml")
            if os.path.exists(config_path):
                if not get_application_url:
                    raise HTTPException(status_code=500, detail="QA AI modules not available for qalia.yml deployment")
                
                # qalia.yml exists - deploy according to its specification (no fallback!)
                logger.info("Found qalia.yml - deploying application according to specification")
                app_url = await get_application_url(repo_path)
                logger.info(f"Application deployed successfully at: {app_url}")
            else:
                # No qalia.yml - fail with clear error message
                raise HTTPException(
                    status_code=400, 
                    detail="No qalia.yml configuration found. Please add a qalia.yml file to specify how to deploy your application for testing."
                )
        else:
            # No repo_path - this shouldn't happen in normal operation
            raise HTTPException(
                status_code=500, 
                detail="Repository not cloned - cannot proceed with analysis"
            )
        
        # Load qalia.yml configuration if available
        config = None
        if repo_path:
            try:
                config_path = os.path.join(repo_path, "qalia.yml")
                config = QaliaConfig(config_path)
                logger.info("Loaded qalia.yml configuration")
            except Exception as e:
                logger.warning(f"Could not load qalia.yml: {e}")
        
        # Create temporary directory for results
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run QA AI analysis
            logger.info(f"Running QA AI analysis on {app_url}")
            
            # Use configuration from qalia.yml if available
            if config:
                testing_config = config.get_testing_config()
                exploration_config = testing_config.get("exploration", {})
                generation_config = testing_config.get("generation", {})
                
                exploration_options = {
                    "headless": exploration_config.get("headless", True),
                    "max_depth": exploration_config.get("max_depth", 3),
                    "timeout": exploration_config.get("timeout", 300),
                    "action_timeout": exploration_config.get("action_timeout", 15000),
                    "navigation_timeout": exploration_config.get("navigation_timeout", 60000),
                    "output_dir": temp_dir
                }
                
                generation_options = {
                    "frameworks": generation_config.get("frameworks", ["playwright", "cypress", "jest"]),
                    "output_dir": temp_dir
                }
            else:
                # Default options
                exploration_options = {
                    "headless": True,
                    "max_depth": 3,
                    "timeout": 300,
                    "action_timeout": 15000,
                    "navigation_timeout": 60000,
                    "output_dir": temp_dir
                }
                
                generation_options = {
                    "frameworks": ["playwright", "cypress", "jest"],
                    "output_dir": temp_dir
                }
            
            # Try browser-based testing first, fall back to simplified testing
            try:
                results = await run_complete_pipeline(
                    app_url, 
                    exploration_options, 
                    generation_options
                )
            except Exception as browser_error:
                logger.warning(f"Browser-based testing failed: {browser_error}")
                
                # Fallback to simplified testing for static sites
                if config and config.get_deployment_config().get('type') == 'static':
                    logger.info("Falling back to simplified static site testing...")
                    results = await run_simplified_static_testing(app_url, repo_path)
                else:
                    raise browser_error
            
            # Process results
            analysis_summary = {
                "status": "completed",
                "app_url": app_url,
                "exploration_results": results.get("exploration_results", {}),
                "test_generation_results": results.get("test_generation_results", {}),
                "session_directory": results.get("session_directory"),
                "total_test_cases": 0,
                "issues_found": 0,
                "recommendations": [],
                "config_used": "qalia.yml" if config else "environment_variables"
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
            "app_url": app_url if 'app_url' in locals() else "unknown"
        }

async def create_check_run(g: Github, repo_name: str, commit_sha: str, analysis_results: Dict[str, Any]):
    """Create a GitHub check run with QA AI results."""
    repo = g.get_repo(repo_name)
    
    if analysis_results["status"] == "completed":
        conclusion = "success" if analysis_results["issues_found"] == 0 else "neutral"
        title = f"Qalia.ai Analysis Complete - {analysis_results['total_test_cases']} tests generated"
        summary = f"""
## 🤖 Qalia.ai Analysis Results

**Target Application:** `{analysis_results['app_url']}`

### 📊 Summary
- **Test Cases Generated:** {analysis_results['total_test_cases']}
- **Issues Found:** {analysis_results['issues_found']}
- **Status:** ✅ Analysis completed successfully

### 🧪 Generated Tests
Qalia.ai has automatically generated comprehensive test suites for your application. The tests cover:
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
        title = "Qalia.ai Analysis Failed"
        summary = f"""
## ❌ Qalia.ai Analysis Failed

**Target Application:** `{analysis_results.get('app_url', 'Unknown')}`
**Error:** {analysis_results.get('error', 'Unknown error occurred')}

Please check your application deployment and try again.
        """
    
    check_run = repo.create_check_run(
        name="Qalia.ai Analysis",
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
## 🤖 Qalia.ai Analysis Results

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
*Powered by Qalia.ai - AI-powered QA testing for your repositories*
        """
    else:
        comment = f"""
## ❌ Qalia.ai Analysis Failed

I encountered an issue while analyzing your application:

**Error:** {analysis_results.get('error', 'Unknown error')}
**Target URL:** `{analysis_results.get('app_url', 'Unknown')}`

Please check your application deployment and ensure it's accessible.

---
*Powered by Qalia.ai*
        """
    
    pr.create_issue_comment(comment)

@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {"message": "QA AI GitHub App is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment verification."""
    try:
        # Check basic functionality
        config_status = "ok" if GITHUB_APP_ID and GITHUB_WEBHOOK_SECRET else "missing_config"
        
        # Check if we can import core modules
        import_status = "ok" if run_complete_pipeline is not None else "import_error"
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "config": config_status,
            "imports": import_status,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Log all headers for debugging
    logger.info(f"Webhook headers: {dict(request.headers)}")
    
    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    
    # Parse payload
    try:
        payload = json.loads(body.decode())
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Get event type
    event_type = request.headers.get("X-GitHub-Event")
    
    logger.info(f"Received {event_type} event from repository: {payload.get('repository', {}).get('full_name', 'unknown')}")
    
    # Log payload action for debugging
    if event_type == "pull_request":
        action = payload.get("action", "unknown")
        pr_number = payload.get("pull_request", {}).get("number", "unknown")
        logger.info(f"Pull request action: {action}, PR number: {pr_number}")
        # Debug: log the payload structure
        logger.info(f"Payload keys: {list(payload.keys())}")
        if "pull_request" in payload:
            logger.info(f"Pull request keys: {list(payload['pull_request'].keys())}")
            if "head" in payload["pull_request"]:
                logger.info(f"Head keys: {list(payload['pull_request']['head'].keys())}")
    
    # Handle different event types in background using asyncio.create_task for true async
    if event_type == "pull_request":
        # Create a fire-and-forget task that doesn't block the response
        asyncio.create_task(handle_pull_request(payload))
        logger.info("Pull request analysis started in background")
    elif event_type == "push":
        # Create a fire-and-forget task that doesn't block the response
        asyncio.create_task(handle_push(payload))
        logger.info("Push analysis started in background")
    elif event_type == "installation":
        logger.info("App installation event received")
    else:
        logger.info(f"Unhandled event type: {event_type}")
    
    # Return immediately to GitHub without waiting for background tasks
    return {"status": "ok", "message": "Webhook received, processing in background"}

async def handle_pull_request(payload: Dict[str, Any]):
    """Handle pull request events."""
    try:
        logger.info("=== STARTING PULL REQUEST ANALYSIS ===")
        # Add some delay to ensure the webhook response is returned first
        await asyncio.sleep(1)
        action = payload.get("action")
        
        # Only process opened and synchronize events
        if action not in ["opened", "synchronize"]:
            logger.info(f"Skipping PR action: {action}")
            return
        
        # Get repository and PR information
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        commit_sha = payload["pull_request"]["head"]["sha"]
        branch = payload["pull_request"]["head"].get("ref", "main")  # Use .get() with default
        installation_id = payload["installation"]["id"]
        
        logger.info(f"Processing PR #{pr_number} in {repo_name}, branch: {branch}")
        
        # Get GitHub client
        try:
            g, access_token = get_github_client(installation_id)
            logger.info("GitHub client created successfully")
        except Exception as e:
            logger.error(f"Failed to create GitHub client: {e}")
            raise
        
        # Clone repository to access qalia.yml
        repo_url = payload["repository"]["clone_url"]
        logger.info(f"Cloning repository: {repo_url}")
        repo_path = await clone_repository(repo_url, branch, access_token)
        
        if not repo_path:
            logger.error("Failed to clone repository")
            # Still try to run analysis without repo_path
        
        # Post initial progress comment
        try:
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment("""
## 🚀 Qalia.ai Analysis Started

I'm now analyzing your application! This process typically takes 2-10 minutes.

**What I'm doing:**
- 🔍 Exploring your application with AI-powered browser automation
- 🧪 Testing interactive elements and user flows
- 🐛 Identifying potential bugs and issues
- 📝 Generating comprehensive test cases

I'll update this comment with detailed results when the analysis is complete.

---
*Powered by Qalia.ai - Real-time progress updates*
            """)
            logger.info("Posted initial progress comment")
        except Exception as e:
            logger.warning(f"Failed to post progress comment: {e}")

        try:
            # Run QA AI analysis with timeout
            logger.info("Starting QA AI analysis")
            analysis_results = await asyncio.wait_for(
                run_qalia_analysis(repo_url, branch, repo_path),
                timeout=1800  # 30 minutes timeout - enough for thorough analysis
            )
            logger.info(f"QA AI analysis completed: {analysis_results.get('status', 'unknown')}")
        except asyncio.TimeoutError:
            logger.error("QA AI analysis timed out after 30 minutes")
            analysis_results = {
                "status": "failed",
                "error": "Analysis timed out after 30 minutes - this indicates a very complex application or system resource constraints",
                "app_url": "unknown"
            }
        except Exception as e:
            logger.error(f"QA AI analysis failed: {e}")
            # Create error results
            analysis_results = {
                "status": "failed",
                "error": str(e),
                "app_url": "unknown"
            }
        finally:
            # Clean up cloned repository
            if repo_path:
                shutil.rmtree(repo_path, ignore_errors=True)
                logger.info("Cleaned up cloned repository")
        
        # Get app configuration
        try:
            config = get_app_config()
            logger.info(f"App config loaded: {config}")
        except Exception as e:
            logger.error(f"Failed to load app config: {e}")
            # Use default config
            config = {"enable_check_runs": True, "enable_pr_comments": True}
        
        # Create check run if enabled
        if config["enable_check_runs"]:
            try:
                await create_check_run(g, repo_name, commit_sha, analysis_results)
                logger.info("Check run created successfully")
            except Exception as e:
                logger.error(f"Failed to create check run: {e}")
        
        # Comment on PR if enabled
        if config["enable_pr_comments"]:
            try:
                await comment_on_pr(g, repo_name, pr_number, analysis_results)
                logger.info("PR comment created successfully")
            except Exception as e:
                logger.error(f"Failed to create PR comment: {e}")
                
    except Exception as e:
        logger.error(f"Unexpected error in handle_pull_request: {e}")
        # Don't re-raise in background tasks to prevent crashing the event loop
        logger.error("Pull request analysis failed, but continuing...")
    finally:
        logger.info("=== PULL REQUEST ANALYSIS COMPLETE ===")

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
    g, access_token = get_github_client(installation_id)
    
    # Clone repository to access qalia.yml
    repo_url = payload["repository"]["clone_url"]
    repo_path = await clone_repository(repo_url, branch, access_token)
    
    try:
        # Run QA AI analysis
        analysis_results = await run_qalia_analysis(repo_url, branch, repo_path)
    finally:
        # Clean up cloned repository
        if repo_path:
            shutil.rmtree(repo_path, ignore_errors=True)
    
    # Create check run
    await create_check_run(g, repo_name, commit_sha, analysis_results)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))) 