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

app = FastAPI(title="QALIA GitHub App")

# GitHub App configuration
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

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
    if not GITHUB_APP_ID or not GITHUB_APP_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="GitHub App credentials not configured")
    
    # Generate JWT
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 600,  # 10 minutes
        "iss": GITHUB_APP_ID
    }
    
    jwt_token = jwt.encode(
        payload,
        GITHUB_APP_PRIVATE_KEY,
        algorithm="RS256"
    )
    
    # Get installation access token
    g = Github(jwt=jwt_token)
    installation = g.get_installation(installation_id)
    token = installation.get_access_token()
    
    # Return client with installation token
    return Github(token.token)

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
    if event_type == "pull_request":
        await handle_pull_request(payload)
    elif event_type == "push":
        await handle_push(payload)
    
    return JSONResponse({"status": "success"})

async def handle_pull_request(payload: Dict[str, Any]):
    """Handle pull request events."""
    action = payload.get("action")
    if action not in ["opened", "synchronize"]:
        return
    
    pr = payload.get("pull_request", {})
    installation_id = payload.get("installation", {}).get("id")
    
    if not installation_id:
        raise HTTPException(status_code=400, detail="No installation ID provided")
    
    # Get authenticated GitHub client
    g = get_github_client(installation_id)
    
    # TODO: Run QALIA analysis on the PR
    # This will be implemented in the next step

async def handle_push(payload: Dict[str, Any]):
    """Handle push events."""
    # TODO: Implement push event handling
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 