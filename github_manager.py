import os
import time
import asyncio
import httpx
from github import Github, GithubException
from typing import Dict


class GitHubManager:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        
        if not self.token or not self.username:
            raise ValueError("GITHUB_TOKEN and GITHUB_USERNAME must be set in environment")
        
        self.github = Github(self.token)
        self.user = self.github.get_user()
    
    def create_and_deploy(self, task_name: str, files: Dict[str, str]) -> Dict[str, str]:
        """
        Create new repo, push files to gh-pages branch, enable Pages
        Returns: dict with repo_url, commit_sha, pages_url
        """
        # Sanitize repo name
        repo_name = self._sanitize_repo_name(task_name)
        
        print(f"Creating repo: {repo_name}")
        
        try:
            # Delete existing repo if present
            self._delete_repo_if_exists(repo_name)
            
            # Create new public repo with auto_init
            repo = self.user.create_repo(
                repo_name,
                description=f"Auto-generated app for {task_name}",
                private=False,
                auto_init=True  # This creates README and main branch
            )
            
            print(f"Repository created: {repo.html_url}")
            time.sleep(3)  # Wait for GitHub to initialize
            
            # Get main branch SHA (exists because of auto_init=True)
            main_ref = repo.get_git_ref("heads/main")
            main_sha = main_ref.object.sha
            
            # Create gh-pages branch from main
            repo.create_git_ref(ref="refs/heads/gh-pages", sha=main_sha)
            print("Created gh-pages branch")
            
            # Upload all files to gh-pages
            self._upload_files(repo, files, "gh-pages")
            
            # Enable GitHub Pages
            self._enable_pages(repo)
            
            # Get final commit SHA from gh-pages
            gh_pages_ref = repo.get_git_ref("heads/gh-pages")
            commit_sha = gh_pages_ref.object.sha
            
            # Construct Pages URL
            pages_url = f"https://{self.username}.github.io/{repo_name}/"
            
            print(f"Deployment complete: {pages_url}")
            
            return {
                "repo_url": repo.html_url,
                "commit_sha": commit_sha,
                "pages_url": pages_url
            }
            
        except Exception as e:
            print(f"Deployment error: {str(e)}")
            raise Exception(f"GitHub deployment failed: {str(e)}")
    
    def update_repo(self, task_name: str, files: Dict[str, str]) -> Dict[str, str]:
        """
        Update existing repo with new files (for round 2)
        Returns: dict with repo_url, commit_sha, pages_url
        """
        repo_name = self._sanitize_repo_name(task_name)
        
        print(f"Updating repo: {repo_name}")
        
        try:
            repo = self.user.get_repo(repo_name)
            
            # Update files on gh-pages branch
            self._upload_files(repo, files, "gh-pages", is_update=True)
            
            # Get latest commit SHA from gh-pages
            gh_pages_ref = repo.get_git_ref("heads/gh-pages")
            commit_sha = gh_pages_ref.object.sha
            
            pages_url = f"https://{self.username}.github.io/{repo_name}/"
            
            print(f"Update complete: {pages_url}")
            
            return {
                "repo_url": repo.html_url,
                "commit_sha": commit_sha,
                "pages_url": pages_url
            }
            
        except Exception as e:
            print(f"Update error: {str(e)}")
            raise Exception(f"GitHub update failed: {str(e)}")
    
    def _sanitize_repo_name(self, task_name: str) -> str:
        """Convert task name to valid repo name"""
        import re
        name = re.sub(r'[^a-zA-Z0-9\s_-]', '', task_name)
        name = re.sub(r'[\s_]+', '-', name)
        name = name.lower().strip('-')
        return name[:100]
    
    def _delete_repo_if_exists(self, repo_name: str):
        """Delete repo if it already exists"""
        try:
            existing_repo = self.user.get_repo(repo_name)
            existing_repo.delete()
            print(f"Deleted existing repo: {repo_name}")
            time.sleep(3)
        except GithubException:
            pass
    
    def _upload_files(self, repo, files: Dict[str, str], branch: str, is_update: bool = False):
        """Upload multiple files to a specific branch"""
        for filepath, content in files.items():
            try:
                # Try to get existing file first
                try:
                    existing_file = repo.get_contents(filepath, ref=branch)
                    # File exists, update it
                    repo.update_file(
                        filepath,
                        f"Update {filepath}",
                        content,
                        existing_file.sha,
                        branch=branch
                    )
                    print(f"Updated: {filepath}")
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist, create it
                        repo.create_file(
                            filepath,
                            f"Add {filepath}",
                            content,
                            branch=branch
                        )
                        print(f"Created: {filepath}")
                    else:
                        raise
                
            except Exception as e:
                print(f"Error handling {filepath}: {str(e)}")
                raise
    
    def _enable_pages(self, repo):
        """Enable GitHub Pages using REST API directly"""
        url = f"https://api.github.com/repos/{self.username}/{repo.name}/pages"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        # Check if Pages is already enabled
        check_response = httpx.get(url, headers=headers)
        
        if check_response.status_code == 200:
            print(f"GitHub Pages already enabled for {repo.name}")
            return
        
        # Enable Pages with gh-pages branch
        data = {
            "source": {
                "branch": "gh-pages",
                "path": "/"
            }
        }
        
        time.sleep(2)
        
        response = httpx.post(url, headers=headers, json=data)
        
        if response.status_code in [201, 200]:
            print(f"GitHub Pages enabled successfully for {repo.name}")
            time.sleep(3)
        elif response.status_code == 409:
            print(f"GitHub Pages already enabled for {repo.name}")
        else:
            print(f"Warning: Could not enable Pages (status {response.status_code})")
