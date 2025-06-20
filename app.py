import os
import sys
import json
import shutil
import tempfile
import asyncio
import logging
import subprocess  # Move subprocess import to top level
import time  # Add missing time import
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

import hmac
import hashlib
from github import Github
import jwt
import requests
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import QA AI functionality from the current directory
try:
    from main import run_complete_pipeline
    from scripts.run_exploration import run_exploration
    from generators import TestCaseGenerator
    from qalia_config import get_application_url, QaliaConfig
    from workflow_generator import WorkflowGenerator  # Import the workflow generator
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

async def clone_repository(repo_url: str, branch: str = "main", access_token: str = None) -> str:
    """Clone a repository to a temporary directory."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Prepare the URL with authentication if token is provided
        if access_token:
            # Parse the URL and inject the token
            if repo_url.startswith("https://github.com/"):
                auth_url = repo_url.replace("https://", f"https://x-access-token:{access_token}@")
            else:
                auth_url = repo_url
        else:
            auth_url = repo_url
        
        # Clone the repository
        result = subprocess.run(
            ["git", "clone", "-b", branch, auth_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to clone repository: {result.stderr}")
            return None
        
        logger.info(f"Repository cloned successfully to: {temp_dir}")
        return temp_dir
    
    except Exception as e:
        logger.error(f"Exception during repository cloning: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None

async def commit_tests_and_workflows(
    repo_path: str, 
    test_results_dir: str, 
    frameworks: list,
    access_token: str,
    branch: str = "main"
) -> bool:
    """
    Commit generated tests and workflows to the repository.
    
    Args:
        repo_path: Local path to the cloned repository
        test_results_dir: Path to generated test files (relative to repo)
        frameworks: List of frameworks that have tests
        access_token: GitHub access token for authentication
        branch: Branch to commit to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        repo_path = Path(repo_path)
        
        # Copy generated tests to repository
        source_tests = Path(test_results_dir)
        target_tests = repo_path / "qalia-tests"
        
        if source_tests.exists():
            if target_tests.exists():
                shutil.rmtree(target_tests)
            shutil.copytree(source_tests, target_tests)
            logger.info(f"Copied generated tests to {target_tests}")
        
        # Generate GitHub Actions workflows
        generator = WorkflowGenerator(str(repo_path))
        workflows = generator.generate_test_workflows(frameworks, "qalia-tests")
        matrix_workflow = generator.create_test_integration_workflow("qalia-tests")
        workflows.append(matrix_workflow)
        
        logger.info(f"Generated {len(workflows)} workflow files")
        
        # Configure git user (required for commits)
        subprocess.run(["git", "config", "user.name", "Qalia AI"], 
                      cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "qalia@ai-generated.com"], 
                      cwd=repo_path, check=True)
        
        # Check if there are any changes to commit
        status_result = subprocess.run(["git", "status", "--porcelain"], 
                                     cwd=repo_path, capture_output=True, text=True)
        
        if not status_result.stdout.strip():
            logger.info("No changes to commit - tests and workflows are up to date")
            return True
        
        # Add all changes
        subprocess.run(["git", "add", "qalia-tests/", ".github/workflows/qalia-*.yml"], 
                      cwd=repo_path, check=True)
        
        # Create commit message
        commit_message = f"""🤖 Add Qalia generated tests and workflows

- Generated test files for {', '.join(frameworks)} frameworks
- Added GitHub Actions workflows for automated testing
- Tests can be run individually or as a complete suite

Generated by Qalia.ai on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        # Commit changes
        subprocess.run(["git", "commit", "-m", commit_message], 
                      cwd=repo_path, check=True)
        
        # Push to remote
        subprocess.run(["git", "push", "origin", branch], 
                      cwd=repo_path, check=True)
        
        logger.info("Successfully committed and pushed generated tests and workflows")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to commit tests and workflows: {e}")
        return False

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
        
        # Install Playwright browsers - REQUIRED for analysis
        logger.info("Installing Playwright browsers...")
        result = subprocess.run(["python", "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"❌ CRITICAL: Playwright browser installation failed: {result.stderr}")
            logger.info("Playwright chromium installed successfully")
            
    except Exception as e:
        raise RuntimeError(f"❌ CRITICAL: Browser setup failed: {e}. Cannot proceed with analysis without browsers.")
    
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
                    "output_dir": temp_dir,
                    "run_tests": True  # Enable test execution to validate generated tests
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
                    "output_dir": temp_dir,
                    "run_tests": True  # Enable test execution to validate generated tests
                }
            
            # Run browser-based testing - FAIL if it doesn't work (no fallbacks!)
            results = await run_complete_pipeline(
                app_url, 
                exploration_options, 
                generation_options
            )
            
            # Commit generated tests and workflows to repository
            test_execution_results = results.get("test_execution_results", {})
            test_generation_results = results.get("test_generation_results", {})
            
            if test_generation_results and repo_path:
                try:
                    logger.info("🚀 Committing generated tests and workflows to repository...")
                    
                    # Get the frameworks that had tests generated
                    generated_files = test_generation_results.get("generated_files", {})
                    available_frameworks = [fw for fw, files in generated_files.items() if files]
                    
                    if available_frameworks:
                        # Get access token from GitHub client setup
                        installation_id = int(os.getenv("GITHUB_INSTALLATION_ID", "0"))
                        if installation_id > 0:
                            _, access_token = get_github_client(installation_id)
                            
                            # Commit tests and workflows
                            commit_success = await commit_tests_and_workflows(
                                repo_path=repo_path,
                                test_results_dir=test_generation_results.get("output_directory", temp_dir),
                                frameworks=available_frameworks,
                                access_token=access_token,
                                branch=branch
                            )
                            
                            if commit_success:
                                logger.info("✅ Successfully committed tests and workflows")
                                
                                # Trigger workflows immediately using repository dispatch
                                logger.info("🚀 Triggering test workflows for immediate execution...")
                                
                                # Get commit SHA for the committed changes
                                try:
                                    sha_result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                                               cwd=repo_path, capture_output=True, text=True)
                                    commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None
                                except:
                                    commit_sha = None
                                
                                if commit_sha:
                                    # Get GitHub client for triggering workflows
                                    g, _ = get_github_client(installation_id)
                                    repo_name = f"{os.getenv('GITHUB_REPOSITORY_OWNER', '')}/{os.getenv('GITHUB_REPOSITORY_NAME', '')}"
                                    
                                    # If we don't have the repo name from env, try to extract from URL
                                    if not repo_name or repo_name == "/":
                                        if "github.com/" in repo_url:
                                            repo_name = repo_url.split("github.com/")[-1].replace(".git", "")
                                    
                                    trigger_success = await trigger_test_workflows(
                                        g, repo_name, branch, available_frameworks, commit_sha
                                    )
                                    
                                    if trigger_success:
                                        logger.info("✅ Test workflows triggered - individual checks will appear shortly!")
                                    else:
                                        logger.warning("⚠️ Failed to trigger workflows - they will run on next commit")
                                else:
                                    logger.warning("⚠️ Could not get commit SHA - workflows will run on next commit")
                            else:
                                logger.warning("⚠️ Failed to commit tests and workflows - manual integration required")
                        else:
                            logger.warning("⚠️ No GitHub installation ID found - skipping workflow generation")
                    else:
                        logger.info("ℹ️ No test files generated - skipping workflow creation")
                        
                except Exception as e:
                    logger.error(f"Failed to commit tests and workflows: {e}")
                    # Don't fail the entire analysis if workflow generation fails
            else:
                logger.info("ℹ️ Skipping workflow generation - no repository path or test results")
            
            # Process results
            analysis_summary = {
                "status": "completed",
                "app_url": app_url,
                "exploration_results": results.get("exploration_results", {}),
                "test_generation_results": results.get("test_generation_results", {}),
                "test_execution_results": results.get("test_execution_results", {}),  # Add test execution results
                "session_directory": results.get("session_directory"),
                "total_test_cases": 0,
                "issues_found": 0,
                "recommendations": [],
                "config_used": "qalia.yml" if config else "environment_variables",
                "workflows_committed": repo_path is not None,  # Indicate if workflows were created
                "chatgpt_analysis": {
                    "status": "unknown",
                    "error": None
                }
            }
            
            # Extract key metrics
            exploration_summary = results.get("exploration_results", {}).get("exploration_summary", {})
            test_summary = results.get("test_generation_results", {}).get("summary", {})
            
            analysis_summary["total_test_cases"] = test_summary.get("generation_summary", {}).get("total_test_cases", 0)
            analysis_summary["issues_found"] = exploration_summary.get("errors_found", 0)
            
            # Extract ChatGPT analysis status from exploration results
            exploration_results_data = results.get("exploration_results", {})
            logger.info(f"DEBUG: exploration_results_data exists: {bool(exploration_results_data)}")
            logger.info(f"DEBUG: results keys: {list(results.keys())}")
            if exploration_results_data:
                # Check if we have a session directory where ChatGPT analysis files were saved
                session_dir = results.get("session_directory")
                logger.info(f"DEBUG: session_dir: {session_dir}")
                
                # If session_dir is None, this is a critical error - the exploration should have provided it
                if not session_dir:
                    # Try alternative sources once - check exploration_results_data directly
                    session_dir = exploration_results_data.get('session_dir')
                    
                    # If still None, this is a critical failure in the exploration pipeline
                    if not session_dir:
                        raise RuntimeError("❌ CRITICAL: Session directory not provided by exploration pipeline. This indicates a failure in the analysis process.")
                
                if session_dir:
                    # Check if ChatGPT analysis files exist (this means analysis completed)
                    chatgpt_md_path = os.path.join(session_dir, "reports", "chatgpt_bug_analysis.md")
                    chatgpt_json_path = os.path.join(session_dir, "reports", "chatgpt_bug_analysis.json")
                    
                    logger.info(f"DEBUG: Looking for ChatGPT files at:")
                    logger.info(f"DEBUG: MD path: {chatgpt_md_path}")
                    logger.info(f"DEBUG: JSON path: {chatgpt_json_path}")
                    logger.info(f"DEBUG: MD exists: {os.path.exists(chatgpt_md_path)}")
                    logger.info(f"DEBUG: JSON exists: {os.path.exists(chatgpt_json_path)}")
                    
                    if os.path.exists(chatgpt_md_path) and os.path.exists(chatgpt_json_path):
                        # Read the actual ChatGPT analysis content
                        try:
                            with open(chatgpt_md_path, 'r', encoding='utf-8') as f:
                                chatgpt_content = f.read()
                            analysis_summary["chatgpt_analysis"] = {
                                "status": "completed",
                                "content": chatgpt_content,
                                "error": None
                            }
                            logger.info("ChatGPT analysis files found and content loaded successfully")
                        except Exception as e:
                            logger.error(f"Failed to read ChatGPT analysis file: {e}")
                            analysis_summary["chatgpt_analysis"] = {
                                "status": "failed",
                                "error": f"Could not read analysis file: {e}"
                            }
                    else:
                        # Files don't exist, check if there was an error
                        try:
                            import json
                            session_report_path = os.path.join(session_dir, "reports", "session_report.json")
                            if os.path.exists(session_report_path):
                                with open(session_report_path, 'r') as f:
                                    session_data = json.load(f)
                                    chatgpt_info = session_data.get("chatgpt_analysis", {})
                                    analysis_summary["chatgpt_analysis"] = {
                                        "status": chatgpt_info.get("status", "failed"),
                                        "error": chatgpt_info.get("error", "ChatGPT analysis files not found")
                                    }
                        except Exception as e:
                            logger.warning(f"Could not read ChatGPT analysis status from session report: {e}")
                            analysis_summary["chatgpt_analysis"] = {
                                "status": "failed",
                                "error": f"Could not determine ChatGPT status: {e}"
                            }
            
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
        
        # Check ChatGPT analysis status
        chatgpt_status = analysis_results.get("chatgpt_analysis", {}).get("status", "unknown")
        chatgpt_error = analysis_results.get("chatgpt_analysis", {}).get("error", None)
        
        # Check test execution results
        test_execution = analysis_results.get("test_execution_results", {})
        execution_summary = test_execution.get("execution_summary", {})
        
        summary = f"""
## 🤖 Qalia.ai Analysis Results

**Target Application:** `{analysis_results['app_url']}`

### 📊 Summary
- **Test Cases Generated:** {analysis_results['total_test_cases']}
- **Issues Found:** {analysis_results['issues_found']}
- **Status:** ✅ Analysis completed successfully"""

        # Add test execution information
        if test_execution and execution_summary:
            successful_frameworks = execution_summary.get('successful_frameworks', 0)
            total_frameworks = execution_summary.get('total_frameworks_tested', 0)
            if total_frameworks > 0:
                summary += f"""
- **Test Validation:** ✅ {successful_frameworks}/{total_frameworks} frameworks passed execution"""
            else:
                summary += """
- **Test Validation:** ⚠️ Tests not executed"""
        else:
            summary += """
- **Test Validation:** ⚠️ Tests not executed"""

        # Add ChatGPT analysis information
        if chatgpt_status == "completed":
            summary += """
- **AI Analysis:** ✅ Completed with detailed insights"""
        elif chatgpt_status == "failed":
            if chatgpt_error and "OpenAI" in chatgpt_error:
                summary += """
- **AI Analysis:** ⚠️ Failed due to OpenAI API issues"""
            else:
                summary += """
- **AI Analysis:** ⚠️ Failed - check logs for details"""
        else:
            summary += """
- **AI Analysis:** ❓ Status unknown"""

        summary += """

### 🧪 Generated Tests
Qalia.ai has automatically generated comprehensive test suites for your application. The tests cover:
- User interface interactions
- Navigation flows
- Form submissions
- Error handling scenarios"""

        # Add workflow information
        if analysis_results.get("workflows_committed", False):
            summary += """

### 🚀 GitHub Actions Integration
✅ **Individual test workflows have been created!** 

The following GitHub Actions workflows will run automatically:
- 🎭 **Qalia Playwright Tests** - End-to-end browser testing
- 🌲 **Qalia Cypress Tests** - Interactive UI testing  
- 🃏 **Qalia Jest Tests** - Unit and integration testing
- 🤖 **Qalia Generated Tests** - Combined test matrix

These will appear as separate checks on future PRs and commits."""

        # Add test execution details if available
        if test_execution and execution_summary.get('total_frameworks_tested', 0) > 0:
            framework_results = test_execution.get('framework_results', {})
            summary += """

### 🏃 Test Execution Results"""
            for framework, result in framework_results.items():
                status_icon = "✅" if result.get('success', False) else "❌"
                passed = result.get('passed_tests', 0)
                failed = result.get('failed_tests', 0)
                exec_time = result.get('execution_time', 0)
                summary += f"""
- **{framework.title()}:** {status_icon} {passed} passed, {failed} failed ({exec_time:.1f}s)"""

        summary += """

### 🚀 Next Steps"""
        
        if analysis_results.get("workflows_committed", False):
            summary += """
1. ✅ **Tests are ready!** Individual test workflows have been added to your repository
2. 🔄 **Automatic testing** will start on your next commit or PR
3. 📊 **Monitor results** in the "Checks" tab of future PRs
4. 🔧 **Customize tests** by editing files in the `qalia-tests/` directory"""
        else:
            summary += """
1. Download the generated test files from the workflow artifacts
2. Integrate the tests into your CI/CD pipeline
3. Review and customize the tests as needed"""
        
        summary += """
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
        # Check ChatGPT analysis status for detailed reporting
        chatgpt_status = analysis_results.get("chatgpt_analysis", {}).get("status", "unknown")
        chatgpt_error = analysis_results.get("chatgpt_analysis", {}).get("error", None)
        
        logger.info(f"DEBUG: PR Comment - ChatGPT status: {chatgpt_status}")
        logger.info(f"DEBUG: PR Comment - ChatGPT analysis keys: {list(analysis_results.get('chatgpt_analysis', {}).keys())}")
        
        # Build the comment with ChatGPT status information
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

The generated tests are available in the workflow artifacts. You can download and integrate them into your testing pipeline."""

        # Add ChatGPT analysis status information
        if chatgpt_status == "completed":
            # Include the actual ChatGPT analysis content
            chatgpt_content = analysis_results.get("chatgpt_analysis", {}).get("content", "")
            if chatgpt_content:
                comment += f"""

### 🧠 AI Analysis
{chatgpt_content}
"""
            else:
                comment += """

### 🧠 AI Analysis
✅ **Detailed ChatGPT analysis completed** - comprehensive insights and test scenarios generated
"""
        elif chatgpt_status == "failed":
            if chatgpt_error and "OpenAI" in chatgpt_error:
                comment += """

### 🧠 AI Analysis
⚠️ **ChatGPT analysis failed due to OpenAI API issues** - basic test generation completed, but detailed AI insights are unavailable
"""
            elif chatgpt_error:
                comment += f"""

### 🧠 AI Analysis
⚠️ **ChatGPT analysis failed** - {chatgpt_error}
"""
            else:
                comment += """

### 🧠 AI Analysis
⚠️ **ChatGPT analysis failed** - basic test generation completed, but detailed AI insights are unavailable
"""
        else:
            comment += """

### 🧠 AI Analysis
❓ **ChatGPT analysis status unknown** - please check the workflow logs for details
"""

        comment += """

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
## UI Analysis Started

I'm now analyzing your application! This process typically takes 2-10 minutes.

**What I'm doing:**
- Exploring your application with AI-powered browser automation
- Testing interactive elements and user flows until I have an exhaustive fingerprint of your application.
- Identifying potential bugs and issues per user flow
- Generating comprehensive test cases

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

async def trigger_test_workflows(
    g: Github, 
    repo_name: str, 
    branch: str, 
    frameworks: list,
    commit_sha: str
) -> bool:
    """
    Trigger the generated test workflows immediately using repository dispatch.
    
    Args:
        g: GitHub client
        repo_name: Repository name (owner/repo)
        branch: Branch to run tests on
        frameworks: List of frameworks to test
        commit_sha: The commit SHA to test against
        
    Returns:
        True if workflows were triggered successfully
    """
    try:
        repo = g.get_repo(repo_name)
        
        # Trigger each framework workflow
        for framework in frameworks:
            workflow_name = f"qalia-{framework}-tests.yml"
            
            try:
                # Use repository dispatch to trigger workflow
                repo.create_repository_dispatch(
                    event_type=f"qalia-test-{framework}",
                    client_payload={
                        "framework": framework,
                        "commit_sha": commit_sha,
                        "branch": branch,
                        "triggered_by": "qalia_analysis"
                    }
                )
                logger.info(f"✅ Triggered {framework} test workflow")
                
            except Exception as e:
                logger.error(f"Failed to trigger {framework} workflow: {e}")
        
        # Also trigger the matrix workflow
        try:
            repo.create_repository_dispatch(
                event_type="qalia-test-matrix",
                client_payload={
                    "frameworks": frameworks,
                    "commit_sha": commit_sha,
                    "branch": branch,
                    "triggered_by": "qalia_analysis"
                }
            )
            logger.info("✅ Triggered matrix test workflow")
            
        except Exception as e:
            logger.error(f"Failed to trigger matrix workflow: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger test workflows: {e}")
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))) 