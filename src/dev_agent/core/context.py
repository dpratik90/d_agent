from typing import Optional, Dict, List, Set
import os
import json
import hashlib
from pathlib import Path

class ProjectContext:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.context_file = os.path.join(workspace_path, ".dev_agent_context.json")
        self.current_project: Optional[Dict] = None
        self._load_context()

    def _load_context(self):
        """Load the current project context from file."""
        if os.path.exists(self.context_file):
            with open(self.context_file, 'r') as f:
                self.current_project = json.load(f)
        else:
            self.current_project = None

    def _save_context(self):
        """Save the current project context to file."""
        with open(self.context_file, 'w') as f:
            json.dump(self.current_project, f, indent=2)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file's content."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _is_relevant_file(self, file_path: str) -> bool:
        """Determine if a file is relevant for project context."""
        # Ignore common directories and files
        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.env'}
        ignore_files = {'.env', '.gitignore', '.DS_Store'}
        
        path_parts = Path(file_path).parts
        if any(part in ignore_dirs for part in path_parts):
            return False
            
        if Path(file_path).name in ignore_files:
            return False
            
        # Only include source code and configuration files
        relevant_extensions = {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.txt', '.md'}
        return Path(file_path).suffix in relevant_extensions

    def _scan_project_files(self, project_path: str) -> Dict:
        """Scan the project directory and return a dictionary of relevant files and their metadata."""
        files = {}
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, project_path)
                
                if self._is_relevant_file(rel_path):
                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        files[rel_path] = {
                            "type": self._get_file_type(filename),
                            "hash": file_hash,
                            "size": os.path.getsize(file_path),
                            "last_modified": os.path.getmtime(file_path)
                        }
                    except Exception:
                        # Skip files that can't be read
                        continue
        return files

    def _get_file_type(self, filename: str) -> str:
        """Determine the type of a file based on its extension and name."""
        if filename.endswith('.py'):
            return 'python'
        elif filename.endswith('.js'):
            return 'javascript'
        elif filename.endswith('.ts'):
            return 'typescript'
        elif filename in ['requirements.txt', 'requirements-test.txt']:
            return 'requirements'
        elif filename in ['.env', '.env.test']:
            return 'env'
        elif filename == 'package.json':
            return 'package'
        else:
            return 'other'

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Safely get the content of a file."""
        try:
            abs_path = os.path.join(self.workspace_path, file_path)
            if os.path.exists(abs_path):
                with open(abs_path, 'r') as f:
                    return f.read()
        except Exception:
            return None
        return None

    def set_current_project(self, project_name: str, project_type: str, project_path: str):
        """Set the current project context."""
        self.current_project = {
            "name": project_name,
            "type": project_type,
            "path": project_path,
            "files": self._scan_project_files(project_path)
        }
        self._save_context()

    def get_current_project(self) -> Optional[Dict]:
        """Get the current project context."""
        return self.current_project

    def clear_context(self):
        """Clear the current project context."""
        self.current_project = None
        if os.path.exists(self.context_file):
            os.remove(self.context_file) 