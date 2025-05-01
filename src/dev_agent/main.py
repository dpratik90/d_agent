import sys
from pathlib import Path
import os
import re
import json
import typer
import asyncio
from typing import Optional, Dict, Tuple
from .config.settings import Settings
from .core.llm.openai_llm import OpenAILLM
from .core.git.git_manager import GitManager
import tempfile
import subprocess
from .core.context import ProjectContext

# Initialize settings and components
settings = Settings()
llm = OpenAILLM(settings)
git = GitManager(settings)

# Initialize project context
project_context = ProjectContext(git.workspace_path)

# Create Typer app
app = typer.Typer()

@app.command()
def respond(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)")
):
    """Respond to review comments and make necessary code changes."""
    print(f"\n=== Debug: Respond Command ===")
    print(f"Branch name: {branch_name}")
    print("======================================\n")

    try:
        # Get the pull request
        prs = git.repo.get_pulls(state='all', head=branch_name)
        print(f"\n=== Debug: Pull Requests ===")
        print(f"PRs type: {type(prs)}")
        print(f"PRs count: {prs.totalCount}")
        print("======================================\n")
        
        if prs.totalCount == 0:
            typer.echo(f"Error: No pull request found for branch {branch_name}")
            return

        pr = prs[0]
        print(f"\n=== Debug: Pull Request Object ===")
        print(f"PR type: {type(pr)}")
        print(f"PR number: {pr.number}")
        print(f"PR state: {pr.state}")
        print(f"PR title: {pr.title}")
        print("======================================\n")

        print(f"Found pull request: {pr.html_url}")

        # Get all review comments
        comments = pr.get_review_comments()
        print(f"\n=== Debug: Review Comments ===")
        print(f"Comments type: {type(comments)}")
        print(f"Comments count: {comments.totalCount}")
        print("======================================\n")
        
        if comments.totalCount == 0:
            typer.echo("No review comments found")
            return

        # Group comments by file
        file_comments = {}
        for comment in comments:
            print(f"\n=== Debug: Comment Object ===")
            print(f"Comment type: {type(comment)}")
            print(f"Comment ID: {comment.id}")
            print(f"Comment Path: {comment.path}")
            print(f"Comment Position: {comment.position}")
            print(f"Comment Line: {comment.line}")
            print(f"Comment Body: {comment.body}")
            print("======================================\n")
            
            if comment.path not in file_comments:
                file_comments[comment.path] = []
            file_comments[comment.path].append(comment)

        print(f"\n=== Debug: File Comments Dictionary ===")
        for file_path, comments_list in file_comments.items():
            print(f"\nFile: {file_path}")
            print(f"Number of comments: {len(comments_list)}")
            for comment in comments_list:
                print(f"  - Comment ID: {comment.id}")
                print(f"  - Comment Position: {comment.position}")
                print(f"  - Comment Line: {comment.line}")
        print("======================================\n")

        # Process each file
        for file_path, comments in file_comments.items():
            print(f"\nProcessing file: {file_path}")

            try:
                # Get current file content
                file_content = git.repo.get_contents(file_path, ref=branch_name).decoded_content.decode()
                lines = file_content.split('\n')

                # Analyze comments and determine changes needed
                changes_needed = []
                for comment in comments:
                    print(f"\n=== Debug: Processing Comment ===")
                    print(f"Comment ID: {comment.id}")
                    print(f"Comment Line: {comment.line}")
                    print(f"Comment Position: {comment.position}")
                    print("======================================\n")

                    print(f"Sending request to OpenAI...")

                    # Add retry logic for OpenAI API calls
                    max_retries = 3
                    retry_count = 0
                    while retry_count < max_retries:
                        try:
                            # Analyze the comment
                            analysis = llm.analyze_review_comment(comment.body, file_content)
                            print("Analysis generated successfully")
                            print("Analysis:")
                            print("-" * 40)
                            print(analysis)
                            print("-" * 40)

                            # Parse the analysis
                            try:
                                # Clean up the analysis string before parsing
                                analysis = analysis.strip()
                                if analysis.startswith('```json'):
                                    analysis = analysis[7:]
                                if analysis.endswith('```'):
                                    analysis = analysis[:-3]
                                analysis = analysis.strip()
                                
                                print(f"\n=== Debug: JSON Analysis ===")
                                print(f"Analysis before parsing: {analysis}")
                                analysis_dict = json.loads(analysis)
                                print(f"Analysis after parsing: {analysis_dict}")
                                print("======================================\n")

                                if analysis_dict.get("change_needed", False):
                                    print(f"\n=== Debug: Change Needed ===")
                                    print(f"Comment line: {comment.line}")
                                    print(f"Comment position: {comment.position}")
                                    change = {
                                        'comment': comment,
                                        'analysis': analysis_dict,
                                        'position': comment.line or 1
                                    }
                                    print(f"Change position: {change['position']}")
                                    changes_needed.append(change)
                                    print("======================================\n")
                                break  # Success, exit retry loop
                            except json.JSONDecodeError as e:
                                print(f"Error parsing analysis: {e}")
                                print(f"Analysis content: {analysis}")
                                retry_count += 1
                                if retry_count == max_retries:
                                    print("Max retries reached for JSON parsing")
                                    break
                                continue
                        except Exception as e:
                            print(f"Error analyzing review comment: {e}")
                            if "account is not active" in str(e):
                                typer.echo("Error: OpenAI API account is not active. Please check your billing details.")
                                return
                            retry_count += 1
                            if retry_count == max_retries:
                                print("Max retries reached for OpenAI API call")
                                break
                            continue

                print(f"\n=== Debug: Changes Needed ===")
                print(f"Number of changes: {len(changes_needed)}")
                for change in changes_needed:
                    print(f"Change position: {change['position']}")
                    print(f"Change suggested: {change['analysis'].get('suggested_change')[:100]}...")
                print("======================================\n")

                if not changes_needed:
                    print(f"No changes needed for {file_path}")
                    continue

                # Make the changes
                new_lines = lines.copy()
                for change in sorted(changes_needed, key=lambda x: x.get('position', 0), reverse=True):
                    new_code = change['analysis'].get('suggested_change')
                    if new_code:
                        if 'position' in change and change['position'] is not None:
                            line_num = change['position'] - 1  # Convert to 0-based index
                            new_lines[line_num] = new_code
                        else:
                            new_lines.append(new_code)

                # Write the changes
                new_content = '\n'.join(new_lines)
                git.repo.update_file(
                    path=file_path,
                    message=f"Address review comments for {file_path}",
                    content=new_content,
                    sha=git.repo.get_contents(file_path, ref=branch_name).sha,
                    branch=branch_name
                )

                # Respond to the comments
                for change in changes_needed:
                    comment = change['comment']
                    response = f"✅ Addressed: {change['analysis'].get('response', 'Changes made based on review')}"
                    try:
                        # Create a review comment reply
                        pr.create_review_comment(
                            body=response,
                            commit_id=comment.commit_id,
                            path=comment.path,
                            position=comment.position,
                            in_reply_to=comment.id
                        )
                        print(f"Responded to comment: {comment.id}")
                    except Exception as e:
                        print(f"Error responding to comment: {e}")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        typer.echo(f"Successfully responded to review comments: {pr.html_url}")

    except Exception as e:
        typer.echo(f"Error responding to review: {e}")

@app.command()
def generate(
    task: str = typer.Argument(..., help="Task description"),
    branch_name: str = typer.Argument(..., help="Branch name (e.g. my-feature)"),
    create_mr: bool = typer.Option(False, "--create-mr", help="Create merge request"),
    mr_title: str = typer.Option(None, "--mr-title", help="Merge request title")
):
    """Generate code based on task description and create a feature branch."""
    asyncio.run(_generate(task, branch_name, create_mr, mr_title))

async def _generate(
    task: str,
    branch_name: str,
    create_mr: bool,
    mr_title: Optional[str]
):
    """Async implementation of generate command."""
    print(f"\n=== Debug: Generate Command ===")
    print(f"Task: {task}")
    print(f"Branch name: {branch_name}")
    print(f"Create MR: {create_mr}")
    print(f"MR title: {mr_title}")
    print("======================================\n")

    try:
        # Create feature branch
        branch = git.create_feature_branch(branch_name)
        print(f"Created feature branch: {branch}")

        # Get current project context
        current_project = project_context.get_current_project()
        
        # Prepare the prompt based on whether we're updating an existing project
        if current_project:
            # Build context with all relevant files
            file_contexts = []
            for file_path, metadata in current_project['files'].items():
                content = project_context.get_file_content(file_path)
                if content:
                    file_contexts.append(f"File: {file_path}\nType: {metadata['type']}\nContent:\n{content}\n")
            
            # We're updating an existing project
            project_info = f"""Current project: {current_project['name']}
Project type: {current_project['type']}
Project path: {current_project['path']}

Project files:
{'-' * 40}
{'\n'.join(file_contexts)}
{'-' * 40}

Task: {task}

Please update the project to implement this task. For each file that needs to be modified:
1. Preserve existing functionality unless it conflicts with the task
2. Add new functionality required by the task
3. Update any code that needs to be changed
4. Maintain the same coding style and structure
5. Update configuration files (requirements.txt, .env, etc.) if needed

Format your response with file markers as before:
=== FILE: path/to/file ===
[content]
"""
        else:
            # We're creating a new project
            project_info = f"""Task: {task}

Please create a new project to implement this task. Include all necessary:
1. Source code files
2. Configuration files (requirements.txt, .env, etc.)
3. Test files and configurations
4. Documentation

Format your response with file markers as before:
=== FILE: path/to/file ===
[content]
"""

        # Generate code
        generated_code = await llm.generate_code(project_info)
        print("Generated code successfully")

        # Process generated files
        file_pattern = re.compile(
            r"^\s*=+ FILE: ?/?([\w\-/\.]+) =+\s*\n"
            r"(?:```[a-zA-Z]*\n)?"
            r"(.*?)"
            r"(?:\n```)?"
            r"(?=\n\s*=+ FILE: |\n\s*=+ FILE: END =+|\Z)",
            re.DOTALL | re.MULTILINE
        )
        files_written = []
        for match in file_pattern.finditer(generated_code + '\n=== FILE: END ==='):
            file_path, file_content = match.group(1).strip(), match.group(2).strip()
            abs_path = os.path.join(git.workspace_path, file_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'w') as f:
                f.write(file_content)
            files_written.append(file_path)
            print(f"Wrote code to {abs_path}")

        # If no valid file delimiters are found, print raw LLM output to a temp file for debugging
        if not files_written:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.llm_output.txt') as tmpf:
                tmpf.write(generated_code)
                debug_path = tmpf.name
            typer.echo(f"Error: No valid file delimiters (=== FILE: ...) found in LLM output. Generation failed. Raw LLM output saved to {debug_path} for debugging.")
            raise RuntimeError("No valid file delimiters found in LLM output.")

        # Update project context if this is a new project
        if not current_project:
            # Extract project name from the first directory in the path
            project_name = files_written[0].split('/')[0] if files_written else "unknown"
            project_type = "python"  # Default to Python, can be enhanced based on files
            project_path = os.path.join(git.workspace_path, project_name)
            project_context.set_current_project(project_name, project_type, project_path)
        else:
            # Update the project context with new/modified files
            project_context.set_current_project(
                current_project['name'],
                current_project['type'],
                current_project['path']
            )

        # Commit and push changes
        git.commit_changes(f"feat: {task}")
        git.push_changes(branch)
        print("Pushed changes to remote")

        # Create merge request if requested
        if create_mr:
            title = mr_title or f"feat: {task}"
            description = f"Generated code for: {task}"
            mr_url = git.create_merge_request(branch, title, description)
            print(f"Created merge request: {mr_url}")
            return mr_url

    except Exception as e:
        typer.echo(f"Error generating code: {e}")
        raise

@app.command()
def review(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the PR if no issues found")
):
    """Review code changes in a pull request."""
    asyncio.run(_review(branch_name, approve))

async def _review(
    branch_name: str,
    approve: bool
):
    """Async implementation of review command."""
    print(f"\n=== Debug: Review Command ===")
    print(f"Branch name: {branch_name}")
    print(f"Auto approve: {approve}")
    print(f"Reviewer: {settings.GIT_AUTHOR_NAME} <{settings.GIT_AUTHOR_EMAIL}>")
    print("======================================\n")

    try:
        # Get the pull request
        prs = git.repo.get_pulls(state='all', head=branch_name)
        print(f"\n=== Debug: Pull Requests ===")
        print(f"PRs type: {type(prs)}")
        print(f"PRs count: {prs.totalCount}")
        print("======================================\n")
        
        if prs.totalCount == 0:
            typer.echo(f"Error: No pull request found for branch {branch_name}")
            return

        pr = prs[0]
        print(f"\n=== Debug: Pull Request Object ===")
        print(f"PR type: {type(pr)}")
        print(f"PR number: {pr.number}")
        print(f"PR state: {pr.state}")
        print(f"PR title: {pr.title}")
        print("======================================\n")

        print(f"Found pull request: {pr.html_url}")

        # Get the files changed in the PR
        files = pr.get_files()
        has_issues = False

        for file in files:
            print(f"\n=== Debug: Reviewing File ===")
            print(f"File: {file.filename}")
            print(f"Status: {file.status}")
            print(f"Changes: +{file.additions} -{file.deletions}")
            print("======================================\n")

            # Get the file content
            if file.status != "removed":
                content = git.repo.get_contents(file.filename, ref=branch_name).decoded_content.decode()
                
                # Review the code
                review = await llm.review_code(content)
                print(f"\nCode Review for {file.filename}:")
                print("-" * 40)
                print(review)
                print("-" * 40)

                try:
                    # Parse the review response
                    # Expecting format: {"issues": [{"line": int, "message": str}], "summary": str, "has_issues": bool}
                    review_dict = json.loads(review)
                    
                    # Create review comments for each issue
                    if review_dict.get("has_issues", False):
                        has_issues = True
                        for issue in review_dict.get("issues", []):
                            try:
                                # Create a review comment with author information
                                pr.create_review_comment(
                                    body=issue["message"],
                                    commit_id=file.sha,
                                    path=file.filename,
                                    line=issue["line"],
                                    author=f"{settings.GIT_AUTHOR_NAME} <{settings.GIT_AUTHOR_EMAIL}>"
                                )
                                print(f"Created review comment for line {issue['line']}")
                            except Exception as e:
                                print(f"Error creating review comment: {e}")

                except json.JSONDecodeError:
                    # If the review is not in JSON format, post it as a general comment
                    pr.create_issue_comment(
                        f"Review for {file.filename}:\n\n{review}",
                        author=f"{settings.GIT_AUTHOR_NAME} <{settings.GIT_AUTHOR_EMAIL}>"
                    )
                    # Assume there might be issues if we can't parse the response
                    has_issues = True

        # Create the review
        if approve and not has_issues:
            pr.create_review(
                body="All changes look good! 👍",
                event="APPROVE",
                author=f"{settings.GIT_AUTHOR_NAME} <{settings.GIT_AUTHOR_EMAIL}>"
            )
            print("Approved the pull request")
        else:
            event = "COMMENT" if not has_issues else "REQUEST_CHANGES"
            pr.create_review(
                body="Review completed. Please check the comments for details.",
                event=event,
                author=f"{settings.GIT_AUTHOR_NAME} <{settings.GIT_AUTHOR_EMAIL}>"
            )
            print(f"Created review with event: {event}")

        typer.echo(f"Successfully reviewed pull request: {pr.html_url}")

    except Exception as e:
        typer.echo(f"Error reviewing pull request: {e}")
        raise 

@app.command()
def test_generate(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)"),
    create_mr: bool = typer.Option(False, "--create-mr", help="Create merge request after generating tests"),
    mr_title: str = typer.Option(None, "--mr-title", help="Merge request title")
):
    """Generate unit tests for all modules in the feature branch."""
    asyncio.run(_test_generate(branch_name, create_mr, mr_title))

async def _test_generate(branch_name: str, create_mr: bool, mr_title: str):
    print(f"\n=== Debug: Test Generate Command ===")
    print(f"Branch name: {branch_name}")
    print("======================================\n")

    try:
        # Checkout the feature branch
        branch = git.create_feature_branch(branch_name)
        print(f"Checked out branch: {branch}")

        # Scan app/ for Python modules
        app_dir = os.path.join(git.workspace_path, "app")
        tests_dir = os.path.join(git.workspace_path, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        module_files = []
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__init__"):
                    module_path = os.path.join(root, file)
                    module_files.append(module_path)
        print(f"Found {len(module_files)} modules in app/: {module_files}")

        test_files_written = []
        for module_path in module_files:
            with open(module_path, "r") as f:
                module_code = f.read()
            module_name = os.path.splitext(os.path.basename(module_path))[0]
            test_file_name = f"test_{module_name}.py"
            test_file_path = os.path.join(tests_dir, test_file_name)
            print(f"Generating tests for {module_path} -> {test_file_path}")

            # LLM prompt for test generation
            prompt = (
                "Generate comprehensive pytest unit tests for the following FastAPI module. "
                "Cover all functions, edge cases, and error handling. "
                "Output only the test code, no explanations.\n\n"
                "=== MODULE CODE START ===\n"
                f"{module_code}\n"
                "=== MODULE CODE END ==="
            )
            test_code = await llm.generate_code(prompt)

            # Strip any leading === FILE: ... === block and optional triple backticks from LLM output
            test_code_clean = test_code.strip()
            file_block_pattern = re.compile(r"^=+ FILE:.*?=+\s*\n(?:```[a-zA-Z]*\n)?(.*?)(?:\n```)?\s*$", re.DOTALL)
            match = file_block_pattern.match(test_code_clean)
            if match:
                test_code_clean = match.group(1).strip()

            # Write the cleaned test code
            with open(test_file_path, "w") as f:
                f.write(test_code_clean)
            test_files_written.append(test_file_path)
            print(f"Wrote tests to {test_file_path}")

        # Commit and push test files
        if test_files_written:
            git.commit_changes(f"test: add generated unit tests for {branch_name}")
            git.push_changes(branch)
            print("Committed and pushed generated tests.")
            # Optionally create a merge request
            if create_mr:
                title = mr_title or f"test: add generated unit tests for {branch_name}"
                description = f"Generated unit tests for branch: {branch_name}"
                mr_url = git.create_merge_request(branch, title, description)
                print(f"Created merge request: {mr_url}")
        else:
            print("No test files were generated.")

        print("\n=== Test Generation Summary ===")
        for tf in test_files_written:
            print(f"Generated: {tf}")
        print("======================================\n")

    except Exception as e:
        typer.echo(f"Error generating tests: {e}")
        raise

@app.command()
def test_run(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)")
):
    """Run all unit tests for the given feature branch and print a summary."""
    _test_run(branch_name)

def _test_run(branch_name: str):
    print(f"\n=== Debug: Test Run Command ===")
    print(f"Branch name: {branch_name}")
    print("======================================\n")

    try:
        # Checkout the feature branch
        branch = git.create_feature_branch(branch_name)
        print(f"Checked out branch: {branch}")

        # Ensure tests directory exists
        tests_dir = os.path.join(git.workspace_path, "tests")
        if not os.path.isdir(tests_dir):
            print(f"No tests directory found at {tests_dir}. Aborting.")
            return

        # Run pytest in the tests directory
        print(f"Running pytest in {tests_dir} ...")
        result = subprocess.run([
            "pytest", tests_dir, "--maxfail=10", "--disable-warnings", "-v"
        ], capture_output=True, text=True)

        print("\n=== Pytest Output ===")
        print(result.stdout)
        print("====================\n")

        if result.returncode == 0:
            print("All tests passed! ✅")
        else:
            print("Some tests failed. ❌")
            print(result.stderr)
        print(f"Exit code: {result.returncode}")
        return result.returncode

    except Exception as e:
        typer.echo(f"Error running tests: {e}")
        raise

@app.callback()
def main():
    """Developer Agent CLI tool."""
    pass

if __name__ == "__main__":
    app() 