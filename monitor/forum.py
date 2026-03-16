"""
Forum/Blackboard storage module for Minecraft AI Python.
Provides a shared message board for distributed AI agents.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from utils import write_json, read_json

# Get the directory for forum data
FORUM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FORUM_PATH = os.path.join(FORUM_DIR, "forum.json")


def ensure_forum_dir():
    """Ensure the forum data directory exists."""
    if not os.path.isdir(FORUM_DIR):
        os.makedirs(FORUM_DIR, exist_ok=True)


def get_forum_path() -> str:
    """Returns path to forum.json."""
    return FORUM_PATH


def load_forum() -> Dict[str, Any]:
    """Load forum data from JSON file."""
    ensure_forum_dir()
    if os.path.isfile(FORUM_PATH):
        try:
            data = read_json(FORUM_PATH)
            if isinstance(data, dict) and "posts" in data:
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return {"posts": []}


def save_forum(data: Dict[str, Any]) -> None:
    """Save forum data to JSON file."""
    ensure_forum_dir()
    write_json(FORUM_PATH, data)


def generate_id(prefix: str = "post") -> str:
    """Generate unique ID with timestamp."""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Truncate to milliseconds
    return f"{prefix}_{timestamp}"


def get_all_posts() -> List[Dict[str, Any]]:
    """Get all posts sorted by created_at descending."""
    forum = load_forum()
    posts = forum.get("posts", [])
    # Sort by created_at descending (newest first)
    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return posts


def get_post(post_id: str) -> Optional[Dict[str, Any]]:
    """Get single post by ID."""
    forum = load_forum()
    for post in forum.get("posts", []):
        if post.get("id") == post_id:
            return post
    return None


def create_post(title: str, content: str, author: str, author_type: str = "bot") -> Dict[str, Any]:
    """Create a new post."""
    forum = load_forum()
    now = generate_id("post")
    now_timestamp = now.replace("post_", "")

    post = {
        "id": now,
        "title": title,
        "content": content,
        "author": author,
        "author_type": author_type,
        "created_at": now_timestamp,
        "updated_at": now_timestamp,
        "replies": []
    }

    forum["posts"].append(post)
    save_forum(forum)
    return post


def update_post(post_id: str, title: str, content: str) -> Optional[Dict[str, Any]]:
    """Update a post (admin only)."""
    forum = load_forum()
    for post in forum.get("posts", []):
        if post.get("id") == post_id:
            post["title"] = title
            post["content"] = content
            post["updated_at"] = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            save_forum(forum)
            return post
    return None


def delete_post(post_id: str) -> bool:
    """Delete a post (admin only)."""
    forum = load_forum()
    original_count = len(forum.get("posts", []))
    forum["posts"] = [p for p in forum.get("posts", []) if p.get("id") != post_id]
    if len(forum["posts"]) < original_count:
        save_forum(forum)
        return True
    return False


def add_reply(post_id: str, content: str, author: str, author_type: str = "bot") -> Optional[Dict[str, Any]]:
    """Add a reply to a post."""
    forum = load_forum()
    for post in forum.get("posts", []):
        if post.get("id") == post_id:
            reply_id = generate_id("reply")
            reply_timestamp = reply_id.replace("reply_", "")
            reply = {
                "id": reply_id,
                "content": content,
                "author": author,
                "author_type": author_type,
                "created_at": reply_timestamp
            }
            post.setdefault("replies", []).append(reply)
            save_forum(forum)
            return reply
    return None


def delete_reply(post_id: str, reply_id: str) -> bool:
    """Delete a reply (admin only)."""
    forum = load_forum()
    for post in forum.get("posts", []):
        if post.get("id") == post_id:
            original_count = len(post.get("replies", []))
            post["replies"] = [r for r in post.get("replies", []) if r.get("id") != reply_id]
            if len(post["replies"]) < original_count:
                save_forum(forum)
                return True
    return False
