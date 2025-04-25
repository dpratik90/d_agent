import os
from pathlib import Path
from git import Repo
from github import Github
from ...config.settings import Settings
from github.Repository import Repository
from github.GithubException import GithubException

class GitManager:
    def __init__(self, settings: Settings):
        print("\n=== Debug: GitHub Environment Values ===")
        print(f"GITHUB_TOKEN: {settings.GITHUB_TOKEN[:10]}...")  # Only show first 10 chars for security
        print(f"GITHUB_REPO_OWNER: {settings.GITHUB_REPO_OWNER}")
        print(f"GITHUB_REPO_NAME: {settings.GITHUB_REPO_NAME}")
        print("======================================\n")
        
        self.settings = settings
        self.github = Github(settings.GITHUB_TOKEN)
        self.repo = self.github.get_user(settings.GITHUB_REPO_OWNER).get_repo(settings.GITHUB_REPO_NAME)
        self.workspace_path = Path(os.path.expanduser(settings.WORKSPACE_PATH))
        self.default_branch = settings.GIT_DEFAULT_BRANCH
        
        # Initialize local repository
        self._init_local_repo()

    def _init_local_repo(self):
        """Initialize and set up the local Git repository."""
        print("\n=== Debug: Initializing Local Git Repository ===")
        print(f"Workspace path: {self.workspace_path}")
        
        try:
            if not (self.workspace_path / '.git').exists():
                print("Initializing new git repository")
                repo = Repo.init(self.workspace_path)
            else:
                print("Git repository already initialized")
                repo = Repo(self.workspace_path)
            
            # Set up remote with authentication
            remote_url = f"https://{self.settings.GITHUB_TOKEN}@github.com/{self.settings.GITHUB_REPO_OWNER}/{self.settings.GITHUB_REPO_NAME}.git"
            print(f"Setting up remote origin with authentication")
            
            try:
                origin = repo.remote('origin')
                origin.set_url(remote_url)
                print("Updated remote URL with authentication")
            except ValueError:
                origin = repo.create_remote('origin', remote_url)
                print("Created new remote origin")
            
            # Fetch from remote to set up tracking
            print("Fetching from remote")
            origin.fetch()
            print("======================================\n")
            
            self.local_repo = repo
        except Exception as e:
            print(f"Error initializing repository: {str(e)}")
            raise

    def create_feature_branch(self, branch_name: str) -> str:
        """Create and checkout a new feature branch."""
        print(f"\n=== Debug: Creating feature branch ===")
        print(f"Branch name: {branch_name}")
        
        # Remove feature/ prefix if it's already in the branch name
        if branch_name.startswith(f"{self.settings.GIT_FEATURE_BRANCH_PREFIX}/"):
            branch_name = branch_name[len(f"{self.settings.GIT_FEATURE_BRANCH_PREFIX}/"):]
        
        full_branch_name = f"{self.settings.GIT_FEATURE_BRANCH_PREFIX}/{branch_name}"
        print(f"Full branch name: {full_branch_name}")
        
        try:
            # Create branch in GitHub
            print(f"Getting default branch: {self.settings.GIT_DEFAULT_BRANCH}")
            default_branch = self.repo.get_branch(self.settings.GIT_DEFAULT_BRANCH)
            print(f"Default branch SHA: {default_branch.commit.sha}")
            
            print(f"Creating new branch: {full_branch_name}")
            try:
                self.repo.create_git_ref(
                    ref=f"refs/heads/{full_branch_name}",
                    sha=default_branch.commit.sha
                )
                print("Branch created successfully in GitHub")
            except GithubException as e:
                if e.status == 422 and "Reference already exists" in str(e):
                    print("Branch already exists in GitHub")
                else:
                    raise
            
            # Checkout branch locally
            print("Checking out branch locally")
            repo = Repo(self.workspace_path)
            repo.git.checkout('-B', full_branch_name)
            print("Branch checked out locally")
            print("======================================\n")
            
            return full_branch_name
        except Exception as e:
            print(f"Error in branch operations: {str(e)}")
            print("======================================\n")
            raise

    def commit_changes(self, message: str):
        """Commit all changes in the workspace."""
        print("\n=== Debug: Committing changes ===")
        print(f"Commit message: {message}")
        print(f"Workspace path: {self.workspace_path}")
        print(f"Author: {self.settings.GIT_AUTHOR_NAME} <{self.settings.GIT_AUTHOR_EMAIL}>")
        
        try:
            repo = Repo(self.workspace_path)
            print(f"Current branch: {repo.active_branch.name}")
            
            # Add all changes
            print("Adding all changes to staging")
            repo.git.add('--all')
            
            # Commit changes with author information
            print("Creating commit")
            repo.git.commit(
                '-m', message,
                author=f"{self.settings.GIT_AUTHOR_NAME} <{self.settings.GIT_AUTHOR_EMAIL}>"
            )
            print("Commit created successfully")
            print("======================================\n")
        except Exception as e:
            print(f"Error committing changes: {str(e)}")
            print("======================================\n")
            raise

    def push_changes(self, branch: str):
        """Push changes to the remote repository."""
        print("\n=== Debug: Pushing changes ===")
        print(f"Branch: {branch}")
        print(f"Workspace path: {self.workspace_path}")
        
        try:
            repo = Repo(self.workspace_path)
            print(f"Current branch: {repo.active_branch.name}")
            
            # Try to pull changes first
            print("Attempting to pull latest changes")
            try:
                repo.git.pull('origin', branch, '--rebase')
                print("Successfully pulled changes")
            except Exception as e:
                if "couldn't find remote ref" in str(e):
                    print("Remote branch doesn't exist yet, skipping pull")
                else:
                    print(f"Warning: Failed to pull changes: {str(e)}")
            
            # Set upstream and push
            print("Setting upstream branch and pushing")
            repo.git.push('--set-upstream', 'origin', branch, '--force')
            print("Changes pushed successfully")
            print("======================================\n")
        except Exception as e:
            print(f"Error pushing changes: {str(e)}")
            print("======================================\n")
            raise

    def create_merge_request(self, branch: str, title: str, description: str) -> str:
        """Create a merge request for the given branch."""
        print("\n=== Debug: Creating merge request ===")
        print(f"Branch: {branch}")
        print(f"Title: {title}")
        print(f"Description: {description}")
        
        try:
            print("Creating pull request")
            pr = self.repo.create_pull(
                title=title,
                body=description,
                head=branch,
                base=self.settings.GIT_DEFAULT_BRANCH
            )
            print(f"Pull request created successfully: {pr.html_url}")
            print("======================================\n")
            return pr.html_url
        except GithubException as e:
            if e.status == 422 and "A pull request already exists" in str(e):
                print("Pull request already exists, getting existing PR")
                prs = self.repo.get_pulls(state='open', head=branch)
                if prs.totalCount > 0:
                    print(f"Found existing PR: {prs[0].html_url}")
                    print("======================================\n")
                    return prs[0].html_url
            print(f"Error creating pull request: {str(e)}")
            print("======================================\n")
            raise

    def respond_to_comment(self, comment, response: str):
        """Respond to a review comment."""
        print("\n=== Debug: Responding to Comment ===")
        print(f"Comment ID: {comment.id}")
        print(f"Response: {response}")
        
        try:
            # Create a reply to the comment
            comment.create_review_comment_reply(response)
            print("Response posted successfully")
            print("======================================\n")
        except Exception as e:
            print(f"Error responding to comment: {str(e)}")
            print("======================================\n")
            raise