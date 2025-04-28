# Agent Workspace

This is the workspace for the AI agent to create and manage code.

## Project Structure

```
agent_workspace/
├── src/            # Source code
│   └── utils/      # Utility functions
├── tests/          # Test files
├── docs/           # Documentation
├── .gitignore      # Git ignore rules
└── README.md       # This file
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Best Practices

- **Always activate your Python virtual environment before running any `dev_agent` command.**
  - Example:
    ```bash
    source venv/bin/activate
    ```
- Ensure all dependencies are installed in the active environment with:
    ```bash
    pip install -r requirements.txt
    ```
- **Always work in a feature branch (never main) for generated code.**
- **Never manually edit files in `agent_workspace`; use `dev_agent` commands for all changes.**
- **Commit and push changes frequently** to avoid losing work and to keep your remote repository up to date.
- **Review generated code and test before merging** to ensure quality and correctness.
- **Use descriptive branch names and merge request (MR) titles** that reflect the task or feature.
- **Keep your `.env` and secrets secure**; never commit sensitive information to version control.
- **Regularly update dependencies and keep your environment clean** to avoid conflicts and security issues.
- **Reference the `.context` file** for project-specific rules and guidelines enforced by the agent.

## Usage

The agent will use this workspace to:
- Generate and modify code
- Run tests
- Create documentation
- Manage version control

## Development

- All code should be placed in the `src` directory
- Tests should be placed in the `tests` directory
- Documentation should be placed in the `docs` directory

## Example: Generate a FastAPI-based Task Management API Project

You can use the following command to generate a complete FastAPI-based Task Management API with JWT authentication, PostgreSQL integration, and proper project structure:

```bash
dev-agent generate "Create a FastAPI-based Task Management API with JWT authentication, PostgreSQL integration, and proper project structure. Include models, schemas, auth, CRUD, and utils folders under /app." task-management-api --create-mr --mr-title "feat: Generate Task Management API"
```

This will create all necessary files and folders in the `agent_workspace` directory and open a merge request for review.