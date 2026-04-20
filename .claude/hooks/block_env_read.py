#!/usr/bin/env python3
"""PreToolUse hook: block Claude from reading any .env file."""
import json
import sys
from pathlib import Path

data = json.load(sys.stdin)
tool = data.get("tool_name", "")
file_path = data.get("tool_input", {}).get("file_path", "")

if tool == "Read" and Path(file_path).name.startswith(".env"):
    print(
        json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Access to '{file_path}' is blocked — .env files may contain secrets.",
            }
        })
    )
    sys.exit(2)
