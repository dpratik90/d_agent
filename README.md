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