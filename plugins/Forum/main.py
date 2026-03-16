"""
Forum Plugin for Minecraft AI Python.
Enables bots to interact with the shared forum/blackboard.
"""

import os
import sys
import requests
import json

sys.path.append("../../")

from plugin import Plugin
from agent import add_log


def get_monitor_url(agent):
    """Get monitor URL from agent settings."""
    web_monitor = agent.settings.get("web_monitor", {})
    if web_monitor.get("enabled", False):
        port = web_monitor.get("port", 8080)
        return f"http://127.0.0.1:{port}"
    return None


def create_post(agent, title, content):
    """Create a new forum post."""
    monitor_url = get_monitor_url(agent)
    if not monitor_url:
        return "Error: Web monitor is not enabled in settings."

    try:
        response = requests.post(
            f"{monitor_url}/api/forum/posts",
            json={
                "title": title,
                "content": content,
                "author": agent.bot.username,
                "author_type": "bot"
            },
            timeout=5
        )
        if response.status_code == 200:
            add_log(
                title="[Plugin \"Forum\"] Created post",
                content=f"Title: {title}",
                label="plugin"
            )
            return f"Successfully created post '{title}' on the forum."
        return f"Failed to create post: {response.status_code} - {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to forum server. Is the web monitor running?"
    except Exception as e:
        return f"Error creating post: {e}"


def reply_to_post(agent, post_id, content):
    """Reply to an existing post."""
    monitor_url = get_monitor_url(agent)
    if not monitor_url:
        return "Error: Web monitor is not enabled in settings."

    try:
        response = requests.post(
            f"{monitor_url}/api/forum/posts/{post_id}/reply",
            json={
                "content": content,
                "author": agent.bot.username,
                "author_type": "bot"
            },
            timeout=5
        )
        if response.status_code == 200:
            add_log(
                title="[Plugin \"Forum\"] Replied to post",
                content=f"Post ID: {post_id}",
                label="plugin"
            )
            return f"Successfully replied to post {post_id}."
        elif response.status_code == 404:
            return f"Error: Post {post_id} not found."
        return f"Failed to reply: {response.status_code} - {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to forum server. Is the web monitor running?"
    except Exception as e:
        return f"Error replying to post: {e}"


def read_posts(agent, limit=10):
    """Read recent forum posts."""
    monitor_url = get_monitor_url(agent)
    if not monitor_url:
        return "Error: Web monitor is not enabled in settings."

    try:
        response = requests.get(
            f"{monitor_url}/api/forum/posts",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            posts = data.get("posts", [])[:limit]

            if not posts:
                return "No posts found on the forum."

            result = f"Recent forum posts ({len(posts)} of {len(data.get('posts', []))}):\n\n"
            for post in posts:
                author_type = post.get("author_type", "unknown")
                reply_count = len(post.get("replies", []))
                result += f"[{post['id']}] {post['title']}\n"
                result += f"    Author: {post['author']} ({author_type})\n"
                result += f"    Content: {post['content'][:200]}{'...' if len(post['content']) > 200 else ''}\n"
                result += f"    Replies: {reply_count}\n\n"

            add_log(
                title="[Plugin \"Forum\"] Read posts",
                content=f"Read {len(posts)} posts",
                label="plugin"
            )
            return result
        return f"Failed to read posts: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to forum server. Is the web monitor running?"
    except Exception as e:
        return f"Error reading posts: {e}"


def read_post_detail(agent, post_id):
    """Read a specific post with all its replies."""
    monitor_url = get_monitor_url(agent)
    if not monitor_url:
        return "Error: Web monitor is not enabled in settings."

    try:
        response = requests.get(
            f"{monitor_url}/api/forum/posts/{post_id}",
            timeout=5
        )
        if response.status_code == 200:
            post = response.json()

            result = f"Post: {post['title']}\n"
            result += f"ID: {post['id']}\n"
            result += f"Author: {post['author']} ({post.get('author_type', 'unknown')})\n"
            result += f"Created: {post.get('created_at', 'unknown')}\n\n"
            result += f"Content:\n{post['content']}\n\n"

            replies = post.get("replies", [])
            if replies:
                result += f"Replies ({len(replies)}):\n"
                for reply in replies:
                    result += f"  - [{reply.get('author_type', 'unknown')}] {reply['author']}: {reply['content']}\n"
            else:
                result += "No replies yet.\n"

            return result
        elif response.status_code == 404:
            return f"Error: Post {post_id} not found."
        return f"Failed to read post: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to forum server. Is the web monitor running?"
    except Exception as e:
        return f"Error reading post: {e}"


def delete_my_post(agent, post_id):
    """Delete own post (bots can only delete their own posts)."""
    monitor_url = get_monitor_url(agent)
    if not monitor_url:
        return "Error: Web monitor is not enabled in settings."

    try:
        # First verify the post belongs to this bot
        check_response = requests.get(
            f"{monitor_url}/api/forum/posts/{post_id}",
            timeout=5
        )
        if check_response.status_code == 404:
            return f"Error: Post {post_id} not found."

        if check_response.status_code == 200:
            post = check_response.json()
            if post.get("author") != agent.bot.username:
                return "Error: You can only delete your own posts."

            # Now delete the post
            response = requests.delete(
                f"{monitor_url}/api/forum/posts/{post_id}",
                timeout=5
            )
            if response.status_code == 200:
                add_log(
                    title="[Plugin \"Forum\"] Deleted post",
                    content=f"Post ID: {post_id}",
                    label="plugin"
                )
                return f"Successfully deleted post {post_id}."
            return f"Failed to delete post: {response.status_code}"

        return f"Failed to verify post ownership: {check_response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to forum server. Is the web monitor running?"
    except Exception as e:
        return f"Error deleting post: {e}"


class PluginInstance(Plugin):
    def __init__(self, agent):
        super().__init__(agent)
        self.plugin_name = "Forum"
        self.reminder = """
You have access to a shared forum/blackboard where you can share information with other bots.
Use forum actions to:
- Share discoveries (ores, structures, dangers, interesting locations)
- Coordinate tasks with other bots
- Request help from other bots
- Report completed tasks
- Read what other bots have shared

Check the forum regularly to stay informed about what others are doing!
"""

    def get_actions(self):
        return [
            {
                "name": "forum_create_post",
                "description": "Create a new post on the shared forum to share information with other bots. Use this to share discoveries, coordinate tasks, or request help.",
                "params": {
                    "title": {"type": "string", "description": "Brief, descriptive title for the post (e.g., 'Found diamonds at spawn', 'Need help building', 'Danger: lava at y=-10')"},
                    "content": {"type": "string", "description": "Detailed content of the post with all relevant information (coordinates, quantities, instructions, etc.)"}
                },
                "perform": create_post
            },
            {
                "name": "forum_reply_post",
                "description": "Reply to an existing forum post. Use this to acknowledge, add information, or coordinate with the original poster.",
                "params": {
                    "post_id": {"type": "string", "description": "ID of the post to reply to (from forum_read_posts)"},
                    "content": {"type": "string", "description": "Your reply content"}
                },
                "perform": reply_to_post
            },
            {
                "name": "forum_read_posts",
                "description": "Read recent forum posts to see what other bots have shared. Always check this before starting tasks to coordinate with others.",
                "params": {
                    "limit": {"type": "int", "description": "Number of recent posts to read (default 10, max 50)"}
                },
                "perform": read_posts
            },
            {
                "name": "forum_read_post_detail",
                "description": "Read the full content of a specific post including all replies.",
                "params": {
                    "post_id": {"type": "string", "description": "ID of the post to read in detail"}
                },
                "perform": read_post_detail
            },
            {
                "name": "forum_delete_my_post",
                "description": "Delete a post you created. You can only delete your own posts.",
                "params": {
                    "post_id": {"type": "string", "description": "ID of your post to delete"}
                },
                "perform": delete_my_post
            }
        ]
