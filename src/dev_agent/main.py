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

# Initialize settings and components
settings = Settings()
llm = OpenAILLM(settings)
git = GitManager(settings)

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
async def generate(
    task: str = typer.Argument(..., help="Task description"),
    output_file: str = typer.Argument(..., help="Output file path"),
    branch_name: str = typer.Argument(..., help="Branch name (e.g. my-feature)"),
    create_mr: bool = typer.Option(False, "--create-mr", help="Create merge request"),
    mr_title: str = typer.Option(None, "--mr-title", help="Merge request title")
):
    """Generate code based on task description and create a feature branch."""
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
        typer.echo(f"Error generating code: {e}")
        raise

@app.command()
async def review(
    branch_name: str = typer.Argument(..., help="Branch name (e.g. feature/my-branch)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the PR if no issues found")
):
    """Review code changes in a pull request and provide feedback."""
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