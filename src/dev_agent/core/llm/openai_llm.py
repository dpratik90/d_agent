from .base import LLMInterface
from openai import OpenAI
from ...config.settings import Settings
import re

class OpenAILLM(LLMInterface):
    def __init__(self, settings: Settings):
        print("\n=== Debug: OpenAI LLM Initialization ===")
        print(f"Using model: {settings.DEFAULT_MODEL}")
        print("======================================\n")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.DEFAULT_MODEL

    async def generate_code(self, prompt: str) -> str:
        print("\n=== Debug: Code Generation ===")
        print(f"Prompt: {prompt}")
        print("Sending request to OpenAI...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skilled software developer. Generate code based on the following prompt."},
                    {"role": "user", "content": prompt}
                ]
            )
            generated_code = response.choices[0].message.content
            print("Code generated successfully")
            print("Generated code:")
            print("----------------------------------------")
            print(generated_code)
            print("----------------------------------------")
            print("======================================\n")
            return generated_code
        except Exception as e:
            print(f"Error generating code: {str(e)}")
            print("======================================\n")
            raise

    async def review_code(self, code: str) -> str:
        print("\n=== Debug: Code Review ===")
        print("Code to review:")
        print("----------------------------------------")
        print(code)
        print("----------------------------------------")
        print("Sending request to OpenAI...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skilled code reviewer. Review the following code and provide feedback."},
                    {"role": "user", "content": code}
                ]
            )
            review = response.choices[0].message.content
            print("Review generated successfully")
            print("Review:")
            print("----------------------------------------")
            print(review)
            print("----------------------------------------")
            print("======================================\n")
            return review
        except Exception as e:
            print(f"Error generating review: {str(e)}")
            print("======================================\n")
            raise

    async def analyze_review_comment(self, comment: str, code: str) -> str:
        """Analyze a review comment and determine if changes are needed."""
        print("\n=== Debug: Analyzing Review Comment ===")
        print(f"Comment: {comment}")
        print("Sending request to OpenAI...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a skilled code reviewer and developer. 
                    Analyze the review comment and determine if changes are needed to the code.
                    If changes are needed, provide the specific code change and a response to the reviewer.
                    Format your response as a JSON object with the following fields:
                    {
                        "change_needed": boolean indicating if a change is needed,
                        "suggested_change": string with the new code if change is needed,
                        "response": string with a response to the reviewer
                    }
                    
                    IMPORTANT: Make sure your response is valid JSON. Do not include any other text or formatting.
                    Do not include newlines or spaces in the JSON structure, only in string values.
                    """},
                    {"role": "user", "content": f"""Code:
{code}

Review comment:
{comment}

Please analyze if changes are needed and provide the response in the specified JSON format."""}
                ]
            )
            analysis = response.choices[0].message.content
            print("Analysis generated successfully")
            print("Analysis:")
            print("----------------------------------------")
            print(analysis)
            print("----------------------------------------")
            print("======================================\n")
            
            # Clean up the response to handle control characters and ensure valid JSON
            analysis = analysis.strip()
            if analysis.startswith('```json'):
                analysis = analysis[7:]
            if analysis.endswith('```'):
                analysis = analysis[:-3]
            analysis = analysis.strip()
            
            # Remove any newlines and extra spaces in the JSON structure (but keep them in string values)
            analysis = re.sub(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', '', analysis)
            
            return analysis
        except Exception as e:
            print(f"Error analyzing review comment: {str(e)}")
            print("======================================\n")
            raise