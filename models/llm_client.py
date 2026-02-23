import json
import ast
import re
from typing import Dict, Any
import ollama

import time

def call_ollama_json(prompt: str, max_retries: int = 3) -> Dict[str, Any]:
    """Helper to call Ollama and enforce JSON extraction robustly."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = ollama.chat(
                model='llama3.1',
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'format': 'json'}
            )
            content = response['message']['content']
            
            # 1. Direct parse attempt (Fast Path)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

            # 2. Extract from markdown blocks explicitly
            json_match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if json_match:
                content_cleaned = json_match.group(1).strip()
            else:
                content_cleaned = content.strip()

            # 3. Aggressive Brackets Extraction
            start_idx = content_cleaned.find('{')
            end_idx = content_cleaned.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = content_cleaned[start_idx:end_idx+1]
                
                # Sanitization for common Model Hallucinations
                json_str = re.sub(r"',\s*\]", "']", json_str) # Trailing commas in arrays (single quotes)
                json_str = re.sub(r'",\s*\]', '"]', json_str) # Trailing commas in arrays (double quotes)
                json_str = re.sub(r",\s*\}", "}", json_str)   # Trailing commas in objects
                
                # Try parsing cleaned string
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # If it's a python dict with single quotes, ast.literal_eval handles it safely
                    try:
                        return ast.literal_eval(json_str)
                    except (SyntaxError, ValueError) as de:
                         raise ValueError(f"Failed to decode parsed dictionary block: {str(de)}\nRaw block:\n{json_str[:200]}...")
            else:
                raise ValueError(f"No JSON object '{{...}}' found in output. Raw: {content[:100]}...")
                
        except Exception as e:
            raw = response.get('message', {}).get('content', 'No content') if 'response' in locals() else 'No response object'
            last_error = f"Failed to decode JSON from Ollama. Error: {str(e)} | Raw: {raw[:100]}..."
            print(f"DEBUG (Attempt {attempt+1}/{max_retries}) - {last_error}")
            time.sleep(1) # Small delay before retry
            
    raise Exception(f"Max retries reached. Last error: {last_error}")

def call_ollama_text(prompt: str, temperature: float = 0.7) -> str:
    """Helper to call Ollama for raw streaming text generation."""
    response = ollama.chat(
        model='llama3.1',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': temperature}
    )
    return response['message']['content'].strip()
