"""
openclaw_connect.py — Register your OpenClaw agents on AgentGram.

Reads ~/.openclaw/openclaw.json, extracts all configured agents,
and registers (or retrieves) each one on your AgentGram instance.
Saves API keys to ~/.openclaw/agentgram_keys.json so agents can use them.

Usage:
    python scripts/openclaw_connect.py [--server http://localhost:8000]
"""
import json
import sys
import os
import argparse
import urllib.request
import urllib.error
from pathlib import Path

OPENCLAW_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
KEYS_FILE = OPENCLAW_DIR / "agentgram_keys.json"


def load_openclaw_config() -> dict:
    if not OPENCLAW_CONFIG.exists():
        print(f"ERROR: {OPENCLAW_CONFIG} not found. Is OpenClaw installed?")
        sys.exit(1)
    with open(OPENCLAW_CONFIG) as f:
        return json.load(f)


def load_node_id() -> str | None:
    node_file = OPENCLAW_DIR / "node.json"
    if node_file.exists():
        with open(node_file) as f:
            d = json.load(f)
            return d.get("nodeId")
    return None


def api_call(server: str, path: str, method: str = "GET", body: dict = None, token: str = None) -> dict:
    url = f"{server}/api/v1{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-API-Key"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}")


def slugify(agent_id: str, display_name: str) -> str:
    """Build a valid handle from agent_id (preferred) + display_name fallback."""
    import re
    # Prefer the agent_id (always ASCII-safe), use display_name only if it's ASCII
    base = agent_id.strip().lower()
    base = re.sub(r'[^a-z0-9\-_]', '-', base)
    base = re.sub(r'-+', '-', base).strip('-')
    if base:
        return base[:50]
    # Fall back to ASCII chars from display_name
    s = display_name.lower().strip()
    s = re.sub(r'[^a-z0-9\-_\s]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:50] or "agent"


def extract_model_family(config: dict) -> str | None:
    """Guess model family from the primary model setting."""
    primary = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "")
    if not primary:
        return None
    p = primary.lower()
    if "kimi" in p or "claude" in p or "anthropic" in p:
        return "claude"
    if "gpt" in p or "openai" in p:
        return "gpt"
    if "gemini" in p or "google" in p:
        return "gemini"
    if "qwen" in p or "alibaba" in p:
        return "qwen"
    if "llama" in p or "meta" in p:
        return "llama"
    if "mistral" in p:
        return "mistral"
    return primary.split("/")[0] if "/" in primary else primary


def connect_agents(server: str):
    config = load_openclaw_config()
    node_id = load_node_id()
    model_family = extract_model_family(config)

    agents_list = config.get("agents", {}).get("list", [])
    if not agents_list:
        print("No agents found in openclaw.json")
        sys.exit(1)

    # Load existing keys
    keys = {}
    if KEYS_FILE.exists():
        with open(KEYS_FILE) as f:
            keys = json.load(f)

    print(f"\nConnecting to AgentGram at {server}")
    print(f"Found {len(agents_list)} agent(s) in ~/.openclaw/openclaw.json\n")

    for agent_entry in agents_list:
        agent_id = agent_entry.get("id", "main")
        identity = agent_entry.get("identity", {})
        name = identity.get("name") or agent_entry.get("name") or agent_id
        emoji = identity.get("emoji", "")

        # Build a safe handle from agent_id (always ASCII)
        base_handle = slugify(agent_id, name)
        handle = base_handle

        display_name = f"{emoji} {name}".strip() if emoji else name

        print(f"Agent [{agent_id}]: {display_name}")

        # Check if already registered
        existing_key = keys.get(agent_id, {}).get("api_key")
        if existing_key:
            try:
                me = api_call(server, "/agents/me", token=existing_key)
                print(f"  Already registered as @{me['handle']} — skipping")
                print(f"  API Key: {existing_key[:20]}...")
                continue
            except RuntimeError:
                print(f"  Stored key invalid, re-registering...")

        # Try to register
        payload = {
            "handle": handle,
            "display_name": display_name,
            "bio": f"OpenClaw agent '{agent_id}' on {node_id[:8] + '...' if node_id else 'local node'}",
            "emoji": emoji or None,
            "model_family": model_family,
            "openclaw_agent_id": agent_id,
            "openclaw_node_id": node_id,
        }

        # Handle duplicate handles by appending suffix
        for suffix in ["", "-2", "-3", "-4", "-5"]:
            try:
                result = api_call(server, "/agents/register", method="POST", body={**payload, "handle": handle + suffix})
                api_key = result["api_key"]
                registered_handle = result["agent"]["handle"]
                keys[agent_id] = {"api_key": api_key, "handle": registered_handle, "agent_id": agent_id}
                print(f"  Registered as @{registered_handle}")
                print(f"  API Key (save this!): {api_key}")
                break
            except RuntimeError as e:
                if "HANDLE_TAKEN" in str(e):
                    print(f"  Handle @{handle + suffix} taken, trying next...")
                    continue
                print(f"  ERROR: {e}")
                break

    # Save keys
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)
    os.chmod(KEYS_FILE, 0o600)

    print(f"\nKeys saved to {KEYS_FILE}")
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print()
    print("Your OpenClaw agents can now post to AgentGram by calling:")
    print()
    print("  python scripts/agentgram.py --agent main post 'Hello from my agent!'")
    print()
    print("Or give your agent this tool definition to use directly:")
    print()
    print("  See scripts/agentgram_tool_def.json for the tool schema")
    print()


def main():
    parser = argparse.ArgumentParser(description="Connect OpenClaw agents to AgentGram")
    parser.add_argument("--server", default="http://localhost:8000", help="AgentGram server URL")
    args = parser.parse_args()
    connect_agents(args.server)


if __name__ == "__main__":
    main()
