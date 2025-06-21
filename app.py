#!/usr/bin/env python3
"""
Qalia QA AI - GitHub Integration Server

This FastAPI server handles GitHub webhooks and coordinates QA analysis
using the Qalia AI system. It processes pull requests and push events,
performs automated QA analysis, and provides feedback through GitHub.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from github_operations import GitHubManager, get_private_key
from main import analyze_web_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/qalia.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global GitHub manager instance
github_manager: GitHubManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for the FastAPI app."""
    global github_manager
    
    # Initialize GitHub manager
    try:
        app_id = os.getenv("GITHUB_APP_ID")
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        private_key = get_private_key()
        
        if not app_id:
            raise ValueError("GITHUB_APP_ID environment variable not set")
        
        github_manager = GitHubManager(
            app_id=app_id,
            private_key=private_key,
            webhook_secret=webhook_secret
        )
        
        logger.info("✅ GitHub manager initialized successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize GitHub manager: {e}")
        raise
    
    yield
    
    # Cleanup if needed
    logger.info("🔄 Shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Qalia QA AI - GitHub Integration",
    description="AI-powered QA testing system with GitHub integration",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Qalia QA AI GitHub Integration Server", "status": "running"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "github_manager": github_manager is not None,
        "timestamp": asyncio.get_event_loop().time()
    }


@app.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    try:
        # Get request body and headers
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        event_type = request.headers.get("X-GitHub-Event", "")
        
        # Verify webhook signature
        if not github_manager.verify_webhook_signature(body, signature):
            logger.error("❌ Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        logger.info(f"📥 Received {event_type} webhook event")
        
        # Route webhook events
        if event_type == "pull_request":
            asyncio.create_task(handle_pull_request(payload))
        elif event_type == "push":
            asyncio.create_task(handle_push(payload))
        else:
            logger.info(f"ℹ️ Ignoring {event_type} event")
        
        return JSONResponse({"status": "received"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        
        # INFINITE LOOP PREVENTION: Check if this is a Qalia-generated commit
        if github_manager.is_qalia_commit(payload):
            logger.info("🔄 Detected Qalia-generated commit - skipping analysis to prevent infinite loop")
            return
        
        # Extract PR information
        pr_info = payload["pull_request"]
        repo_name = payload["repository"]["full_name"]
        pr_number = pr_info["number"]
        branch = pr_info["head"]["ref"]
        commit_sha = pr_info["head"]["sha"]
        repo_url = payload["repository"]["clone_url"]
        installation_id = payload["installation"]["id"]
        
        logger.info(f"🔍 Analyzing PR #{pr_number} in {repo_name} (branch: {branch})")
        
        # Perform QA analysis
        await perform_qa_analysis(
            repo_name=repo_name,
            repo_url=repo_url,
            branch=branch,
            commit_sha=commit_sha,
            pr_number=pr_number,
            installation_id=installation_id,
            event_type="pull_request"
        )
        
    except Exception as e:
        logger.error(f"❌ Pull request handling error: {e}")


async def handle_push(payload: Dict[str, Any]):
    """Handle push events."""
    try:
        logger.info("=== STARTING PUSH ANALYSIS ===")
        
        # INFINITE LOOP PREVENTION: Check if this is a Qalia-generated commit
        if github_manager.is_qalia_commit(payload):
            logger.info("🔄 Detected Qalia-generated commit - skipping analysis to prevent infinite loop")
            return
        
        # Only process pushes to main/master branches
        ref = payload.get("ref", "")
        if not any(branch in ref for branch in ["main", "master"]):
            logger.info(f"Skipping push to {ref} - only analyzing main/master branches")
            return
        
        # Extract push information
        repo_name = payload["repository"]["full_name"]
        branch = ref.split("/")[-1]  # Extract branch name from refs/heads/branch
        commit_sha = payload["head_commit"]["id"]
        repo_url = payload["repository"]["clone_url"]
        installation_id = payload["installation"]["id"]
        
        logger.info(f"🔍 Analyzing push to {repo_name}:{branch}")
        
        # Perform QA analysis
        await perform_qa_analysis(
            repo_name=repo_name,
            repo_url=repo_url,
            branch=branch,
            commit_sha=commit_sha,
            installation_id=installation_id,
            event_type="push"
        )
        
    except Exception as e:
        logger.error(f"❌ Push handling error: {e}")


async def perform_qa_analysis(
    repo_name: str,
    repo_url: str,
    branch: str,
    commit_sha: str,
    installation_id: int,
    event_type: str,
    pr_number: int = None
):
    """Perform QA analysis on the repository."""
    repo_path = None
    
    try:
        logger.info(f"🤖 Starting QA analysis for {repo_name}:{branch}")
        
        # Get GitHub client and access token
        g, access_token = github_manager.get_client(installation_id)
        
        # Clone repository
        repo_path = await github_manager.clone_repository(repo_url, branch, access_token)
        if not repo_path:
            logger.error("❌ Failed to clone repository")
            return
        
        # Run QA analysis
        logger.info("🔍 Running Qalia AI analysis...")
        analysis_results = await analyze_web_app(
            repo_path, 
            installation_id=installation_id
        )
        
        if not analysis_results:
            logger.error("❌ QA analysis failed")
            return
        
        logger.info("✅ QA analysis completed successfully")
        
        # Commit generated tests and workflows
        frameworks = analysis_results.get("test_frameworks", [])
        if frameworks:
            logger.info(f"📝 Committing tests for frameworks: {frameworks}")
            
            success = await github_manager.commit_tests_and_workflows(
                repo_path=repo_path,
                test_results_dir=analysis_results.get("test_results_dir", "qalia-tests"),
                frameworks=frameworks,
                access_token=access_token,
                branch=branch
            )
            
            if success:
                logger.info("✅ Successfully committed tests and workflows")
                
                # Trigger test workflows immediately
                await github_manager.trigger_test_workflows(
                    repo_name=repo_name,
                    branch=branch,
                    frameworks=frameworks,
                    commit_sha=commit_sha,
                    installation_id=installation_id
                )
            else:
                logger.error("❌ Failed to commit tests and workflows")
        
        # Create GitHub check run (TODO: implement in GitHubManager)
        # await github_manager.create_check_run(repo_name, commit_sha, analysis_results)
        
        # Comment on PR if this is a PR event (TODO: implement in GitHubManager)
        # if event_type == "pull_request" and pr_number:
        #     await github_manager.comment_on_pr(repo_name, pr_number, analysis_results)
        
        logger.info("🎉 QA analysis pipeline completed successfully")
                
    except Exception as e:
        logger.error(f"❌ QA analysis error: {e}")
    
    finally:
        # Cleanup cloned repository
        if repo_path and os.path.exists(repo_path):
            import shutil
            shutil.rmtree(repo_path, ignore_errors=True)
            logger.info(f"🧹 Cleaned up temporary repository: {repo_path}")
    

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting Qalia QA AI server on port {port}")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    ) 