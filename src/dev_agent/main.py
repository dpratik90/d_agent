import sys
from pathlib import Path
import os
import re
import json
import typer
import asyncio
import black
from typing import Optional, Dict, Tuple
from .config.settings import Settings
from .core.llm.openai_llm import OpenAILLM
from .core.git.git_manager import GitManager

# Initialize settings and components
settings = Settings()
llm = OpenAILLM(settings)
git = GitManager(settings)

# Create Typer app
app = typer.Typer()

def run_async_command(coro):
    """Helper function to run async commands."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        print(f"Error running async command: {e}")
        raise typer.Exit(1)

@app.command()
def respond(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)")
):
    """Respond to review comments and make necessary code changes."""
    return run_async_command(_respond(branch_name))

async def _respond(branch_name: str):
    """Async implementation of respond command."""
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

        # Get all submitted review comments
        comments = pr.get_review_comments()
        print(f"\n=== Debug: Review Comments ===")
        print(f"Comments type: {type(comments)}")
        print(f"Comments count: {comments.totalCount}")
        print("======================================\n")
        
        if comments.totalCount == 0:
            typer.echo("No submitted review comments found")
            return

        # Group comments by file
        file_comments = {}
        for comment in comments:
            print(f"\n=== Debug: Comment Object ===")
            print(f"Comment type: {type(comment)}")
            print(f"Comment ID: {comment.id}")
            print(f"Comment Path: {comment.path}")
            print(f"Comment Position: {comment.position}")
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
        print("======================================\n")

        # Process each file
        for file_path, comments in file_comments.items():
            print(f"\nProcessing file: {file_path}")

            try:
                # Check if file exists in the workspace
                if not os.path.exists(file_path):
                    print(f"File {file_path} does not exist in workspace. Skipping file changes.")
                    # Still respond to comments even if file doesn't exist
                    for comment in comments:
                        try:
                            analysis = await llm.analyze_review_comment(comment.body, "")
                            analysis_dict = None
                            try:
                                analysis_dict = json.loads(analysis)
                            except json.JSONDecodeError as e:
                                print(f"Error parsing analysis JSON: {e}")
                                print(f"Raw analysis: {analysis}")
                                continue
                            
                            if not analysis_dict:
                                continue
                            
                            # Reply to the comment
                            try:
                                pr.create_review_comment(
                                    body=analysis_dict.get('response', 'No response provided.'),
                                    commit=comment.commit_id,
                                    path=comment.path,
                                    position=comment.position,
                                    in_reply_to=comment.id
                                )
                            except Exception as e:
                                print(f"Error creating comment reply: {e}")
                                # Fallback to issue comment
                                try:
                                    pr.create_issue_comment(
                                        f"In response to comment on {comment.path}:\n\n{comment.body}\n\n{analysis_dict.get('response', 'No response provided.')}"
                                    )
                                except Exception as e:
                                    print(f"Error creating fallback issue comment: {e}")
                        except Exception as e:
                            print(f"Error processing comment: {e}")
                    continue

                # Get current file content
                with open(file_path, 'r') as f:
                    file_content = f.read()
                lines = file_content.split('\n')

                # Analyze comments and determine changes needed
                changes_needed = []
                for comment in comments:
                    print(f"\n=== Debug: Processing Comment ===")
                    print(f"Comment ID: {comment.id}")
                    print(f"Comment Position: {comment.position}")
                    print("======================================\n")

                    print(f"Sending request to OpenAI...")

                    # Add retry logic for OpenAI API calls
                    max_retries = 3
                    retry_count = 0
                    while retry_count < max_retries:
                        try:
                            # Analyze the comment
                            analysis = await llm.analyze_review_comment(comment.body, file_content)
                            print("Analysis generated successfully")
                            print("Analysis:")
                            print("-" * 40)
                            print(analysis)
                            print("-" * 40)

                            # Parse the analysis
                            analysis_dict = None
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
                            except json.JSONDecodeError as e:
                                print(f"Error parsing analysis: {e}")
                                print(f"Analysis content: {analysis}")
                                retry_count += 1
                                if retry_count == max_retries:
                                    print("Max retries reached for JSON parsing")
                                    break
                                continue

                            if not analysis_dict:
                                continue

                            if analysis_dict.get("change_needed", False):
                                print(f"\n=== Debug: Change Needed ===")
                                print(f"Comment position: {comment.position}")
                                change = {
                                    'comment': comment,
                                    'analysis': analysis_dict,
                                    'position': comment.position or 1
                                }
                                print(f"Change position: {change['position']}")
                                changes_needed.append(change)
                                print("======================================\n")

                            # Always respond to the comment
                            try:
                                pr.create_review_comment(
                                    body=analysis_dict.get('response', 'No response provided.'),
                                    commit=comment.commit_id,
                                    path=comment.path,
                                    position=comment.position,
                                    in_reply_to=comment.id
                                )
                            except Exception as e:
                                print(f"Error creating comment reply: {e}")
                                # Fallback to issue comment
                                try:
                                    pr.create_issue_comment(
                                        f"In response to comment on {comment.path}:\n\n{comment.body}\n\n{analysis_dict.get('response', 'No response provided.')}"
                                    )
                                except Exception as e:
                                    print(f"Error creating fallback issue comment: {e}")

                            break  # Success, exit retry loop
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

                # Apply changes if needed
                if changes_needed:
                    # Sort changes by position in reverse order to avoid line number issues
                    changes_needed.sort(key=lambda x: x['position'], reverse=True)
                    
                    # Get the suggested changes
                    suggested_changes = [change['analysis'].get('suggested_change') for change in changes_needed]
                    
                    # Format the code using black
                    try:
                        formatted_code = black.format_str('\n'.join(suggested_changes), mode=black.FileMode())
                        print("\nFormatted code:")
                        print("-" * 40)
                        print(formatted_code)
                        print("-" * 40)
                    except Exception as e:
                        print(f"Error formatting code: {e}")
                        formatted_code = '\n'.join(suggested_changes)
                    
                    # Write the formatted code back to the file
                    try:
                        with open(file_path, 'w') as f:
                            f.write(formatted_code)
                        print(f"\nSuccessfully wrote changes to {file_path}")
                    except Exception as e:
                        print(f"Error writing changes to file: {e}")
                        continue

                    # Commit and push changes
                    try:
                        git.repo.index.add([file_path])
                        git.repo.index.commit(f"Apply review comments to {file_path}")
                        git.repo.remote().push(branch_name)
                        print(f"\nSuccessfully pushed changes to {branch_name}")
                    except Exception as e:
                        print(f"Error committing and pushing changes: {e}")
                        continue

            except FileNotFoundError:
                print(f"File not found: {file_path}")
                continue
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue

        print(f"\nSuccessfully responded to review comments for PR: {pr.html_url}")

    except Exception as e:
        print(f"Error in respond command: {e}")
        raise typer.Exit(1)

@app.command()
def generate(
    task: str = typer.Argument(..., help="Task description"),
    output_file: str = typer.Argument(..., help="Output file path"),
    branch_name: str = typer.Argument(..., help="Branch name (e.g. my-feature)"),
    create_mr: bool = typer.Option(False, "--create-mr", help="Create merge request"),
    mr_title: str = typer.Option(None, "--mr-title", help="Merge request title")
):
    """Generate code based on task description and create a feature branch."""
    return run_async_command(_generate(task, output_file, branch_name, create_mr, mr_title))

async def _generate(
    task: str,
    output_file: str,
    branch_name: str,
    create_mr: bool,
    mr_title: Optional[str]
):
    """Async implementation of generate command."""
    print(f"\n=== Debug: Generate Command ===")
    print(f"Task: {task}")
    print(f"Output file: {output_file}")
    print(f"Branch name: {branch_name}")
    print(f"Create MR: {create_mr}")
    print(f"MR title: {mr_title}")
    print("======================================\n")

    try:
        # Create feature branch
        branch = git.create_feature_branch(branch_name)
        print(f"Created feature branch: {branch}")

        # Generate code
        generated_code = await llm.generate_code(task)
        print("Generated code successfully")

        # Write code to file
        output_path = os.path.join(git.workspace_path, output_file)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(generated_code)
        print(f"Wrote code to {output_path}")

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
        print(f"Error generating code: {e}")
        raise typer.Exit(1)

@app.command()
def review(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the PR if no issues found")
):
    """Review code changes in a pull request and provide feedback."""
    return run_async_command(_review(branch_name, approve))

async def _review(branch_name: str, approve: bool):
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

            # Get the file
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

        print(f"Successfully reviewed pull request: {pr.html_url}")

    except Exception as e:
        print(f"Error reviewing pull request: {e}")
        raise typer.Exit(1) 