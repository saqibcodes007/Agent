# main.py (Definitive Production Version)

import io
import os
import base64
import uuid
from datetime import datetime
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from agent import Agent
import planner

app = FastAPI(title="RCM Agent API")

# A simple in-memory "database" to store the state of our tasks
TASK_STATE_DATABASE = {}

@app.get("/")
async def get_ui():
    """Serves the main HTML user interface."""
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/start-task")
async def start_task(command: str = Body(..., embed=True)):
    """Starts a new agent task and returns a unique ID for it."""
    task_id = str(uuid.uuid4())
    TASK_STATE_DATABASE[task_id] = {
        "command": command,
        "history": [],
        "agent": Agent()
    }
    await TASK_STATE_DATABASE[task_id]["agent"].start()
    print(f"New task started with ID: {task_id}")
    return {"task_id": task_id}

@app.post("/run-next-step")
async def run_next_step(task_id: str = Body(..., embed=True)):
    """Runs the next single step for a given task."""
    if task_id not in TASK_STATE_DATABASE:
        raise HTTPException(status_code=404, detail="Task not found")

    state = TASK_STATE_DATABASE[task_id]
    agent = state["agent"]

    try:
        screenshot_bytes = await agent.get_screenshot()
        page_html = await agent.get_html()
        current_url = await agent.get_current_url()

        action_plan = planner.generate_action_plan(
            command=state["command"],
            screenshot_bytes=screenshot_bytes,
            page_html=page_html,
            current_url=current_url,
            history=state["history"]
        )
        
        code_to_execute = action_plan.get("code")
        reasoning = action_plan.get("reasoning", "No reasoning provided.")

        if code_to_execute == "FINISH":
            print("Planner has finished the task.")
            final_screenshot_bytes = await agent.get_screenshot(full_page=True)
            await agent.save_screenshot(final_screenshot_bytes)
            await agent.stop()
            del TASK_STATE_DATABASE[task_id]
            screenshot_base64 = base64.b64encode(final_screenshot_bytes).decode('utf-8')
            return {"status": "finished", "reason": reasoning, "screenshot": f"data:image/png;base64,{screenshot_base64}"}

        if code_to_execute == "PAUSE_FOR_HUMAN":
            print("Planner is pausing for human intervention.")
            await agent.stop()
            del TASK_STATE_DATABASE[task_id]
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            return {"status": "human_required", "reason": reasoning, "screenshot": f"data:image/png;base64,{screenshot_base64}"}

        success, error_message = await agent.perform_action(code_to_execute)
        
        action_plan_for_history = action_plan.copy()
        action_plan_for_history["status"] = "SUCCESS" if success else "ERROR"
        if not success:
            action_plan_for_history["error_message"] = error_message
        state["history"].append(action_plan_for_history)

        return {"status": "continue", "reason": reasoning, "last_action_status": "SUCCESS" if success else "ERROR"}

    except Exception as e:
        if task_id in TASK_STATE_DATABASE:
            await TASK_STATE_DATABASE[task_id]["agent"].stop()
            del TASK_STATE_DATABASE[task_id]
        print(f"A critical error occurred: {e}")
        return {"status": "error", "reason": f"A critical error occurred: {e}"}