"""
Sandbox file for testing gw pull conflict handling.

Edit the CONFLICT_LINE below on two branches differently to trigger a merge conflict.
"""

APP_NAME = "Gitwise pull demo"
VERSION = "1.0.0"

# CONFLICT_LINE — change this line on main AND on your test branch (different text each time)
GREETING = "Hello updated from test branch"

def describe() -> str:
    return f"{APP_NAME} v{VERSION}: {GREETING}"
