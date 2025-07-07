# planner.py (Definitive Production Version)

import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-2.5-flash')
generation_config = { "temperature": 0.1, "response_mime_type": "application/json" }

def generate_action_plan(command: str, screenshot_bytes: bytes, page_html: str, current_url: str, history: list) -> dict:
    print("Planner: Asking Vision AI to analyze screenshot and HTML...")
    
    img = Image.open(io.BytesIO(screenshot_bytes))
    formatted_history = json.dumps(history, indent=2)

    prompt = f"""
    You are an expert computer-use agent. Your goal is to achieve the user's command by combining visual analysis from a screenshot with structural analysis from HTML code.

    **PRIMARY DIRECTIVE: DUAL ANALYSIS & PROBLEM SOLVING**
    Analyze the screenshot and HTML to determine the next best action. If a previous action failed, your priority is to recover.

    **CODE GENERATION RULES & ACTION TYPES:**
    - Your generated code MUST be a single line of valid asynchronous Playwright Python code. **You MUST NOT include the `await` keyword in your `code` string.**
    - If the task is complete, generate the code `"FINISH"`.
    - If you encounter a CAPTCHA, generate the code `"PAUSE_FOR_HUMAN"`.

    **PLAYWRIGHT EXAMPLES (DO NOT INCLUDE 'await'):**
    - `page.goto("https://example.com")`
    - `page.locator("button[type='submit']").click()`
    - `page.select_option("select#country", value="IN")`

    ---
    **CONTEXT**
    **User Command:** "{command}"
    **Action History (with status):**
    ```json
    {formatted_history}
    ```
    **Current URL:** {current_url}
    ---
    **Your JSON Response:**
    Your output MUST be a valid JSON object with "reasoning" and "code" keys.
    """
    
    try:
        response = model.generate_content([prompt, img])
        raw_text = response.text
        print(f"Planner: Raw AI Response text:\n---\n{raw_text}\n---")
        
        start_index = raw_text.find('{')
        end_index = raw_text.rfind('}')
        if start_index == -1 or end_index == -1 or end_index < start_index:
            raise ValueError("Could not find a valid JSON object in the AI's response.")
            
        json_string = raw_text[start_index:end_index+1]
        plan = json.loads(json_string)

        print(f"Planner Reasoning: {plan.get('reasoning')}")
        print(f"Planner Code: {plan.get('code')}")
        return plan
    except Exception as e:
        print(f"Planner: AI failed to generate a valid plan. Error: {e}")
        return {"code": "FINISH", "reasoning": f"AI Planner failed with error: {e}"}