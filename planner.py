# planner.py (With PAUSE capability)

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
    
    formatted_history = json.dumps(history, indent=2)
    img = Image.open(io.BytesIO(screenshot_bytes))

    prompt = f"""
    You are an expert computer-use agent. Your goal is to achieve the user's command by combining visual analysis from a screenshot with structural analysis from HTML code.

    **PRIMARY DIRECTIVE: DUAL ANALYSIS & PROBLEM SOLVING**
    Analyze the screenshot and HTML to determine the next best action. If a previous action failed, your priority is to recover.

    **CAPTCHA HANDLING:**
    If you analyze the screenshot and HTML and identify a CAPTCHA challenge (e.g., an `iframe` with 'reCAPTCHA' in its name, a "I'm not a robot" checkbox, or a "select all images with..." prompt), your action MUST be `PAUSE`.

    **CODE GENERATION RULES & ACTION TYPES:**
    - Your generated code MUST be a single line of valid asynchronous Playwright Python code.
    - You have access to the `page` object.
    - Action code can be `page.goto(...)`, `page.locator(...).click()`, `page.select_option(...)`, `page.keyboard.press(...)`, etc.
    - If the task is complete, generate the code `"FINISH"`.
    - If you encounter a CAPTCHA, generate the code `"PAUSE_FOR_HUMAN"`.

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
    ```json
    {{
        "reasoning": "A step-by-step explanation of what you see and why you are generating this code.",
        "code": "page.locator('...').click()"
    }}
    ```
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
