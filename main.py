# main.py (With PAUSE capability)

import io
import base64
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from agent import Agent
import planner

app = FastAPI(title="RCM Agent API")

@app.get("/")
async def get_ui():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/run-agent")
async def execute_command(command: str = Body(..., embed=True)):
    print(f"\n\n--- Received new command: '{command}' ---")
    MAX_STEPS = 30
    history = []

    try:
        async with Agent() as agent:
            for i in range(MAX_STEPS):
                print(f"\n--- Step {i+1}/{MAX_STEPS} ---")
                
                screenshot_bytes = await agent.get_screenshot()
                page_html = await agent.get_html()
                current_url = await agent.get_current_url()
                
                action_plan = planner.generate_action_plan(command, screenshot_bytes, page_html, current_url, history)
                
                code_to_execute = action_plan.get("code")

                if code_to_execute == "FINISH" or code_to_execute is None:
                    print("Planner has finished the task.")
                    final_screenshot = await agent.get_screenshot(full_page=True)
                    # For a finish, we return the image directly
                    return HTMLResponse(content=final_screenshot, media_type="image/png")
                
                # --- THIS IS THE NEW LOGIC ---
                if code_to_execute == "PAUSE_FOR_HUMAN":
                    print("Planner is pausing for human intervention.")
                    # For a pause, we return a JSON object with a status and the image
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    return JSONResponse(content={
                        "status": "human_required",
                        "message": action_plan.get("reasoning", "CAPTCHA detected. Please solve it and run the command again."),
                        "screenshot": f"data:image/png;base64,{screenshot_base64}"
                    })
                # ---------------------------------
                
                success, error_message = await agent.perform_action(code_to_execute)
                
                action_plan_for_history = action_plan.copy()
                action_plan_for_history["status"] = "SUCCESS" if success else "ERROR"
                if not success:
                    action_plan_for_history["error_message"] = error_message
                history.append(action_plan_for_history)

            raise Exception("Agent has reached the maximum number of steps.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
