def review_code(self, code: str) -> str:
    """Review the given code and provide feedback."""
    prompt = f"""Please review the following code and provide feedback on:
1. Code quality and style
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Suggestions for improvement

Code:
{code}

Please provide your review in a clear and constructive manner."""

    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": "You are a code reviewer. Provide detailed, constructive feedback on the code."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content

def analyze_review_comment(self, comment: str, code: str) -> str:
    """Analyze a review comment and determine if changes are needed."""
    prompt = f"""Please analyze the following review comment and code, and determine if changes are needed.
If changes are needed, provide the updated code and a response to the comment.

Review Comment:
{comment}

Current Code:
{code}

Please respond in the following JSON format, with all strings properly escaped and no line breaks in the output:
{{"change_needed": boolean, "suggested_change": "code here", "response": "response here"}}

IMPORTANT: Your response must be a single line of valid JSON with properly escaped strings. Do not include any line breaks in strings."""

    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": "You are a code reviewer. Analyze the review comment and determine if changes are needed. Your response must be a single line of valid JSON with properly escaped strings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # Clean up the response to ensure it's valid JSON
    analysis = response.choices[0].message.content.strip()
    # Remove any markdown code block markers
    analysis = analysis.replace('```json', '').replace('```', '')
    # Remove any newlines and extra whitespace
    analysis = ' '.join(analysis.split())
    # Ensure proper escaping of quotes
    analysis = analysis.replace('\\"', '"').replace('"', '\\"')
    # Wrap in quotes if needed
    if not analysis.startswith('{'):
        analysis = '{' + analysis
    if not analysis.endswith('}'):
        analysis = analysis + '}'
    return analysis 