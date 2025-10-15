import os
import base64
import time
import httpx
from github import Github, GithubException
from typing import Dict, Optional

class GitHubManager:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        self.g = Github(self.token)
        self.user = self.g.get_user()
    
    def create_repo(self, task_id: str) -> Dict[str, str]:
        """Create a new public GitHub repository"""
        repo_name = f"llm-app-{task_id}"
        
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=f"Auto-generated app for task {task_id}",
                private=False,
                auto_init=True
            )
            return {
                "repo_url": repo.html_url,
                "repo_name": repo_name,
                "repo": repo
            }
        except GithubException as e:
            if e.status == 422:  # Repo already exists
                repo = self.user.get_repo(repo_name)
                return {
                    "repo_url": repo.html_url,
                    "repo_name": repo_name,
                    "repo": repo
                }
            raise
    
    def add_files(self, repo, files: Dict[str, str], commit_message: str = "Initial commit"):
        """Add multiple files to repository"""
        for file_path, content in files.items():
            try:
                # Check if file exists
                try:
                    existing = repo.get_contents(file_path)
                    repo.update_file(
                        path=file_path,
                        message=commit_message,
                        content=content,
                        sha=existing.sha
                    )
                except GithubException:
                    # File doesn't exist, create it
                    repo.create_file(
                        path=file_path,
                        message=commit_message,
                        content=content
                    )
            except Exception as e:
                print(f"Error adding file {file_path}: {e}")
                raise
    
    def get_latest_commit_sha(self, repo) -> str:
        """Get the latest commit SHA"""
        commits = repo.get_commits()
        return commits[0].sha
    
    def enable_pages(self, repo) -> str:
        """Enable GitHub Pages and return the URL"""
        pages_url = f"https://{self.username}.github.io/{repo.name}/"
        
        try:
            # Enable Pages via API
            url = f"https://api.github.com/repos/{self.username}/{repo.name}/pages"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json"
            }
            data = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            
            response = httpx.post(url, headers=headers, json=data)
            
            if response.status_code in [201, 409]:  # Created or already exists
                return pages_url
            else:
                print(f"Pages enable response: {response.status_code} - {response.text}")
                return pages_url
                
        except Exception as e:
            print(f"Error enabling pages: {e}")
            return pages_url
    
    async def wait_for_pages_live(self, pages_url: str, max_attempts: int = 30) -> bool:
        """Wait for GitHub Pages to be live (up to 2 minutes)"""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(pages_url, timeout=10)
                    if response.status_code == 200:
                        print(f"Pages live at {pages_url}")
                        return True
                except:
                    pass
                
                await asyncio.sleep(4)  # Wait 4 seconds between attempts
        
        return False
