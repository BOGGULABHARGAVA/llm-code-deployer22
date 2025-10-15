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
from github_manager_old import GitHubManager
from app_generator_old import AppGenerator
from dotenv import load_dotenv
load_dotenv()
import os

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
    
    # Verify secret
    if request.secret != SECRET or request.email != STUDENT_EMAIL:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if already processed
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
    
    # Store task
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
    
    # Queue background job
    background_tasks.add_task(
        process_deployment,
        request.dict()
    )
    
    return {"status": "ok", "message": "Deployment queued"}

async def process_deployment(request_data: Dict):
    """Background task to handle deployment"""
    try:
        print(f"Processing deployment for task: {request_data['task']}, round: {request_data['round']}")
        
        # Initialize managers
        github_mgr = GitHubManager()
        app_gen = AppGenerator()
        
        # Detect task type
        task_type = app_gen.detect_task_type(request_data['brief'])
        print(f"Detected task type: {task_type}")
        
        # Generate app files
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
            print(f"Unknown task type, using generic generator")
            # Fallback to generic
            files = {"index.html": "<html><body><h1>Generic App</h1></body></html>"}
            files["LICENSE"] = app_gen._get_mit_license()
            files["README.md"] = app_gen._generate_readme("App", request_data['brief'], request_data['checks'])
        
        # Create or update repo
        repo_info = github_mgr.create_repo(request_data['task'])
        repo = repo_info['repo']
        
        # Add files
        commit_msg = f"Round {request_data['round']}: {request_data['brief'][:50]}"
        github_mgr.add_files(repo, files, commit_msg)
        
        # Get commit SHA
        commit_sha = github_mgr.get_latest_commit_sha(repo)
        
        # Enable Pages
        pages_url = github_mgr.enable_pages(repo)
        
        # Wait for Pages to be live
        is_live = await github_mgr.wait_for_pages_live(pages_url)
        
        if not is_live:
            print(f"Warning: Pages might not be live yet at {pages_url}")
        
        # Notify evaluator
        await notify_evaluator(
            request_data['evaluation_url'],
            {
                "email": request_data['email'],
                "task": request_data['task'],
                "round": request_data['round'],
                "nonce": request_data['nonce'],
                "repo_url": repo_info['repo_url'],
                "commit_sha": commit_sha,
                "pages_url": pages_url
            }
        )
        
        # Save to database
        async with async_session_maker() as db:
            repo_entry = Repo(
                email=request_data['email'],
                task=request_data['task'],
                round=request_data['round'],
                nonce=request_data['nonce'],
                repo_url=repo_info['repo_url'],
                commit_sha=commit_sha,
                pages_url=pages_url,
                notify_status="success",
                notify_timestamp=datetime.utcnow()
            )
            db.add(repo_entry)
            await db.commit()
        
        print(f"Deployment complete: {pages_url}")
        
    except Exception as e:
        print(f"Error in deployment: {e}")
        import traceback
        traceback.print_exc()

async def notify_evaluator(evaluation_url: str, payload: Dict, max_retries: int = 5):
    """Notify evaluator with exponential backoff"""
    delays = [1, 2, 4, 8, 16]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt, delay in enumerate(delays[:max_retries]):
            try:
                response = await client.post(
                    evaluation_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"Successfully notified evaluator: {evaluation_url}")
                    return True
                else:
                    print(f"Evaluator response {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"Notification attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
    
    print(f"Failed to notify evaluator after {max_retries} attempts")
    return False

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "email": STUDENT_EMAIL,
        "endpoint": "/api-endpoint"
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
