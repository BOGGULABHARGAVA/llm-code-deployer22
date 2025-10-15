import os
import asyncio
import hashlib
from datetime import datetime
from typing import Dict
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from database import init_db, get_session, Task, Repo
from github_manager import GitHubManager
from app_generator import AppGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="LLM Code Deployer")

# Load environment
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL")
SECRET = os.getenv("SECRET")


class DeployRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: list[str]
    evaluation_url: str
    attachments: list[Dict] = []


class EvaluationPayload(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: str
    commit_sha: str
    pages_url: str


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()
    print("Database initialized")


@app.post("/api-endpoint")
async def deploy_endpoint(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """Main endpoint to receive deployment requests"""
    
    # Verify credentials
    if request.secret != SECRET or request.email != STUDENT_EMAIL:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if already processed (idempotency)
    result = await db.execute(
        select(Task).where(
            Task.email == request.email,
            Task.task == request.task,
            Task.round == request.round,
            Task.nonce == request.nonce
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return {"status": "already_processed", "nonce": request.nonce}
    
    # Store task in database
    task = Task(
        email=request.email,
        task=request.task,
        round=request.round,
        nonce=request.nonce,
        brief=request.brief,
        checks=request.checks,
        attachments=request.attachments,
        evaluation_url=request.evaluation_url,
        secret_hash=hashlib.sha256(request.secret.encode()).hexdigest(),
        statuscode=200
    )
    db.add(task)
    await db.commit()
    
    # Queue background deployment job
    background_tasks.add_task(process_deployment, request.dict())
    
    return {"status": "ok", "message": "Deployment queued"}


async def process_deployment(request_data: Dict):
    """Background task to handle the entire deployment workflow"""
    try:
        print(f"Processing deployment for task: {request_data['task']}, round: {request_data['round']}")
        
        # Initialize managers
        app_gen = AppGenerator()
        github_mgr = GitHubManager()
        
        # Detect task type from brief
        task_type = app_gen.detect_task_type(request_data['brief'])
        print(f"Detected task type: {task_type}")
        
        # Generate app files based on task type
        files = None
        if task_type == "captcha-solver":
            files = app_gen.generate_captcha_solver(
                request_data['brief'],
                request_data['checks'],
                request_data['attachments']
            )
        elif task_type == "sum-of-sales":
            files = app_gen.generate_sum_of_sales(
                request_data['brief'],
                request_data['checks'],
                request_data['attachments'],
                request_data['round']
            )
        elif task_type == "markdown-to-html":
            files = app_gen.generate_markdown_to_html(
                request_data['brief'],
                request_data['checks'],
                request_data['attachments'],
                request_data['round']
            )
        elif task_type == "github-user-created":
            files = app_gen.generate_github_user_created(
                request_data['brief'],
                request_data['checks'],
                request_data['attachments'],
                request_data['round']
            )
        else:
            # Fallback to generic app
            print(f"Using generic template for unknown task type")
            files = {
                "index.html": "<html><body><h1>Generic Application</h1></body></html>",
                "LICENSE": app_gen._get_mit_license(),
                "README.md": app_gen._generate_readme("Application", request_data['brief'], request_data['checks'])
            }
        
        if not files:
            raise ValueError("No files generated")
        
        print(f"Generated {len(files)} files")
        
        # Deploy to GitHub
        if request_data['round'] == 1:
            # Round 1: Create new repo and deploy
            result = github_mgr.create_and_deploy(request_data['task'], files)
        else:
            # Round 2+: Update existing repo
            result = github_mgr.update_repo(request_data['task'], files)
        
        print(f"Deployed successfully:")
        print(f"  Repo URL: {result['repo_url']}")
        print(f"  Commit SHA: {result['commit_sha']}")
        print(f"  Pages URL: {result['pages_url']}")
        
        # Prepare evaluation payload
        evaluation_payload = {
            "email": request_data['email'],
            "task": request_data['task'],
            "round": request_data['round'],
            "nonce": request_data['nonce'],
            "repo_url": result['repo_url'],
            "commit_sha": result['commit_sha'],
            "pages_url": result['pages_url']
        }
        
        # Notify evaluator with retry logic
        notify_success = await send_with_retry(
            request_data['evaluation_url'],
            evaluation_payload
        )
        
        # Save repo info to database
        async for db in get_session():
            repo_entry = Repo(
                email=request_data['email'],
                task=request_data['task'],
                round=request_data['round'],
                nonce=request_data['nonce'],
                repo_url=result['repo_url'],
                commit_sha=result['commit_sha'],
                pages_url=result['pages_url'],
                notify_status="success" if notify_success else "failed",
                notify_timestamp=datetime.utcnow()
            )
            db.add(repo_entry)
            await db.commit()
            break
        
        print(f"Deployment workflow complete for {request_data['task']}")
        
    except Exception as e:
        print(f"Error in deployment: {str(e)}")
        import traceback
        traceback.print_exc()


async def send_with_retry(url: str, payload: Dict, max_retries: int = 5) -> bool:
    """Send POST request with exponential backoff retry"""
    delays = [1, 2, 4, 8, 16]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                print(f"Sending notification to {url} (attempt {attempt + 1}/{max_retries})")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"✓ Successfully notified evaluator")
                    return True
                else:
                    print(f"⚠ Evaluator returned {response.status_code}: {response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"⚠ Timeout on attempt {attempt + 1}")
            except Exception as e:
                print(f"⚠ Error on attempt {attempt + 1}: {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                delay = delays[attempt]
                print(f"  Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    
    print(f"✗ Failed to notify evaluator after {max_retries} attempts")
    return False


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "status": "running",
        "service": "LLM Code Deployer",
        "email": STUDENT_EMAIL,
        "endpoint": "/api-endpoint",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
