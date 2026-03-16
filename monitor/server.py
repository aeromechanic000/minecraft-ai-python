"""
FastAPI-based web monitor server for Minecraft AI Python.
Provides a web interface to view bot status, history, and 3D world view.
Also provides a forum/blackboard API for distributed AI agents.
"""

import os
import json
import threading
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from utils import read_json, get_datetime_stamp
from monitor import forum

app = FastAPI(title="Minecraft AI Monitor")

# Get the directory where this file is located
MONITOR_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(MONITOR_DIR, "templates")
BOTS_DIR = os.path.join(os.path.dirname(MONITOR_DIR), "bots")
SETTINGS_PATH = os.path.join(os.path.dirname(MONITOR_DIR), "settings.json")


def get_bot_dirs() -> List[str]:
    """Get list of bot directories."""
    if not os.path.isdir(BOTS_DIR):
        return []
    return [d for d in os.listdir(BOTS_DIR)
            if os.path.isdir(os.path.join(BOTS_DIR, d))]


def get_bot_state_path(username: str) -> str:
    """Get path to bot's state.json file."""
    return os.path.join(BOTS_DIR, username, "monitor", "state.json")


def get_bot_memory_path(username: str) -> str:
    """Get path to bot's memory.json file."""
    return os.path.join(BOTS_DIR, username, "memory.json")


def get_bot_decision_history_path(username: str) -> str:
    """Get path to bot's decision_history.json file."""
    return os.path.join(BOTS_DIR, username, "decision_history.json")


def read_state(username: str) -> Optional[Dict[str, Any]]:
    """Read bot state from file."""
    state_path = get_bot_state_path(username)
    if os.path.isfile(state_path):
        try:
            return read_json(state_path)
        except (json.JSONDecodeError, Exception):
            return None
    return None


def read_memory(username: str) -> Optional[Dict[str, Any]]:
    """Read bot memory from file."""
    memory_path = get_bot_memory_path(username)
    if os.path.isfile(memory_path):
        try:
            return read_json(memory_path)
        except (json.JSONDecodeError, Exception):
            return None
    return None


def read_decision_history(username: str) -> List[Dict[str, Any]]:
    """Read bot decision history from file."""
    history_path = get_bot_decision_history_path(username)
    if os.path.isfile(history_path):
        try:
            data = read_json(history_path)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return []


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main HTML page with injected settings."""
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            html_content = f.read()

        # Inject viewer_enabled setting
        try:
            settings = read_json(SETTINGS_PATH)
            web_monitor = settings.get("web_monitor", {})
            viewer_enabled = web_monitor.get("viewer_enabled", True)
        except Exception:
            viewer_enabled = True

        inject_script = f'<script>window.WEB_MONITOR_CONFIG = {{ viewer_enabled: {str(viewer_enabled).lower()} }};</script>'
        html_content = html_content.replace('</head>', f'{inject_script}</head>')

        return html_content
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/api/bots")
async def list_bots():
    """List all bots with their current status.

    Only includes bots that have recent state updates (actively running).
    Bots without state data or with stale state are excluded.
    """
    bots = []
    for username in get_bot_dirs():
        state = read_state(username)
        if state is not None:
            # Only include bots with valid state data (actively running)
            # A bot without a timestamp or with empty data is not running
            timestamp = state.get("timestamp", "")
            if timestamp and len(timestamp) > 0:
                bots.append({
                    "username": username,
                    "position": state.get("position", {"x": 0, "y": 0, "z": 0}),
                    "health": state.get("health", 0),
                    "hunger": state.get("hunger", 0),
                    "status_summary": state.get("status_summary", ""),
                    "current_action": state.get("current_action", ""),
                    "timestamp": timestamp,
                    "viewer_port": state.get("viewer_port"),
                    "current_goal": state.get("current_goal"),
                })
    return {"bots": bots}


@app.get("/api/bots/{username}")
async def get_bot_detail(username: str):
    """Get detailed information about a specific bot."""
    if username not in get_bot_dirs():
        raise HTTPException(status_code=404, detail="Bot not found")

    state = read_state(username)
    if state is None:
        state = {
            "username": username,
            "status_summary": "No state data available",
        }

    return state


@app.get("/api/bots/{username}/history")
async def get_bot_history(username: str):
    """Get action/decision history for a specific bot."""
    if username not in get_bot_dirs():
        raise HTTPException(status_code=404, detail="Bot not found")

    decision_history = read_decision_history(username)

    # Also get recent chat/memory records
    memory = read_memory(username)
    chat_history = []
    if memory and "records" in memory:
        for record in memory.get("records", [])[-20:]:  # Last 20 records
            if record.get("type") in ["message", "report", "status"]:
                chat_history.append({
                    "type": record.get("type"),
                    "sender": record.get("data", {}).get("sender", ""),
                    "content": record.get("data", {}).get("content", ""),
                    "time": record.get("time", []),
                })

    return {
        "username": username,
        "decision_history": decision_history,
        "chat_history": chat_history,
    }


class ModeToggleRequest(BaseModel):
    """Request model for toggling a mode."""
    mode_name: str
    on: bool


# Store for pending mode changes (bot will check this periodically)
_pending_mode_changes: Dict[str, Dict[str, bool]] = {}


@app.get("/api/bots/{username}/modes")
async def get_bot_modes(username: str):
    """Get current mode states for a specific bot."""
    state = read_state(username)
    if state is None:
        raise HTTPException(status_code=404, detail="Bot state not found")
    return {"modes": state.get("modes", {})}


@app.put("/api/bots/{username}/modes")
async def set_bot_mode(username: str, request: ModeToggleRequest):
    """Toggle a mode for a specific bot.

    This stores the change request which will be picked up by the bot
    on its next tick update.
    """
    if username not in get_bot_dirs():
        raise HTTPException(status_code=404, detail="Bot not found")

    # Store the pending change
    if username not in _pending_mode_changes:
        _pending_mode_changes[username] = {}
    _pending_mode_changes[username][request.mode_name] = request.on

    return {"success": True, "mode": request.mode_name, "on": request.on}


def get_pending_mode_changes(username: str) -> Dict[str, bool]:
    """Get and clear pending mode changes for a bot."""
    if username in _pending_mode_changes:
        changes = _pending_mode_changes[username].copy()
        _pending_mode_changes[username] = {}
        return changes
    return {}


# ==================== Forum API ====================

class PostCreateRequest(BaseModel):
    """Request model for creating a post."""
    title: str
    content: str
    author: str
    author_type: str = "bot"


class PostUpdateRequest(BaseModel):
    """Request model for updating a post."""
    title: str
    content: str


class ReplyCreateRequest(BaseModel):
    """Request model for creating a reply."""
    content: str
    author: str
    author_type: str = "bot"


@app.get("/api/forum/posts")
async def list_posts():
    """List all forum posts."""
    posts = forum.get_all_posts()
    return {"posts": posts}


@app.post("/api/forum/posts")
async def create_post(request: PostCreateRequest):
    """Create a new post (bot or admin)."""
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    post = forum.create_post(
        title=request.title,
        content=request.content,
        author=request.author,
        author_type=request.author_type
    )
    return {"success": True, "post": post}


@app.get("/api/forum/posts/{post_id}")
async def get_post_detail(post_id: str):
    """Get a specific post with replies."""
    post = forum.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.put("/api/forum/posts/{post_id}")
async def update_post(post_id: str, request: PostUpdateRequest):
    """Update a post (admin only)."""
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    post = forum.update_post(post_id, request.title, request.content)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True, "post": post}


@app.delete("/api/forum/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post (admin only)."""
    success = forum.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True}


@app.post("/api/forum/posts/{post_id}/reply")
async def add_reply(post_id: str, request: ReplyCreateRequest):
    """Add a reply to a post."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    reply = forum.add_reply(
        post_id=post_id,
        content=request.content,
        author=request.author,
        author_type=request.author_type
    )
    if reply is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True, "reply": reply}


@app.delete("/api/forum/posts/{post_id}/replies/{reply_id}")
async def delete_reply(post_id: str, reply_id: str):
    """Delete a reply (admin only)."""
    success = forum.delete_reply(post_id, reply_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post or reply not found")
    return {"success": True}


class MonitorServer:
    """Wrapper class for running FastAPI server in a thread."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def _run_server(self):
        """Run the uvicorn server."""
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        self.running = True
        server.run()

    def start(self):
        """Start the monitor server in a background thread."""
        if self.server_thread is not None and self.server_thread.is_alive():
            return

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        print(f"[Monitor] Web monitor started on http://localhost:{self.port}")

    def stop(self):
        """Stop the monitor server."""
        self.running = False
        # Note: uvicorn doesn't have a clean shutdown mechanism when run in a thread
        # The daemon=True will ensure it terminates when the main process exits
