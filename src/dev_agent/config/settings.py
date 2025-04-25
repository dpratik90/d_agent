import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI settings
    OPENAI_API_KEY: str
    DEFAULT_MODEL: str = "gpt-4"
    
    # Git settings
    GIT_DEFAULT_BRANCH: str = "main"
    GIT_FEATURE_BRANCH_PREFIX: str = "feature"
    GITHUB_TOKEN: str
    GITHUB_REPO_OWNER: str
    GITHUB_REPO_NAME: str
    GIT_AUTHOR_NAME: str = "Dev Agent"
    GIT_AUTHOR_EMAIL: str = "dev-agent@example.com"
    
    # Workspace settings
    WORKSPACE_PATH: Path = Path(os.path.expanduser("~/agent_workspace"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"