#!/usr/bin/env python3
"""Launch the Onshape MCP server with credentials resolved at runtime.

Keys are pulled from the 1Password service account (read-only, no biometric
prompt) each time the server starts, so nothing is written to .env or to any
Claude Code config file.

The service-account token is loaded from disk rather than inherited from the
environment. MCP servers are spawned by their client, and a GUI client (Cursor,
Claude Desktop) never sources ~/.zprofile, so OP_SERVICE_ACCOUNT_TOKEN is absent
there. Without it `op` silently falls back to the desktop-app integration and
fires a Touch ID prompt on every start -- once a minute under a restart loop.
The same empty environment applies to launchd and cron.

The Onshape item in the WalterSignal vault stores both keys inside a field
*label* rather than a value, so they are parsed out of the item JSON.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PY = os.path.join(REPO, ".venv", "bin", "python")
TOKEN_FILE = os.path.expanduser("~/.config/op/service-account-token")

ACCESS_KEY_RE = re.compile(r"\bon_[A-Za-z0-9]{16,}\b")
SECRET_KEY_RE = re.compile(r"secret key is ([A-Za-z0-9]{40,})")


def op_env(home):
    """Environment for `op` with the service-account token guaranteed present.

    Fails closed. Returning an environment without the token would hand the
    caller a Touch ID prompt instead of an error, which is the failure this
    function exists to prevent.

    `home` must be an empty scratch directory. In a GUI/launchd session `op`
    finds the desktop-app integration config under ~/.config/op and tries
    biometric unlock ahead of the token; pointing HOME at an empty directory
    leaves it nothing to find but the token. (Cairn #1947.)
    """
    env = dict(os.environ, HOME=home)
    token = env.get("OP_SERVICE_ACCOUNT_TOKEN")
    if token:
        return env

    if not os.path.exists(TOKEN_FILE):
        sys.exit(
            f"No 1Password service-account token in the environment and none at "
            f"{TOKEN_FILE}. Refusing to fall back to the desktop-app integration, "
            f"which prompts for Touch ID on every start."
        )
    with open(TOKEN_FILE) as fh:
        token = fh.read().strip()
    if not token:
        sys.exit(f"{TOKEN_FILE} is empty")

    env["OP_SERVICE_ACCOUNT_TOKEN"] = token
    return env


def resolve_keys():
    ak, sk = os.getenv("ONSHAPE_ACCESS_KEY"), os.getenv("ONSHAPE_SECRET_KEY")
    if ak and sk:
        return ak, sk

    with tempfile.TemporaryDirectory() as scratch_home:
        result = subprocess.run(
            ["op", "item", "get", "Onshape", "--vault", "WalterSignal", "--format", "json"],
            capture_output=True,
            text=True,
            env=op_env(scratch_home),
        )
    if result.returncode != 0:
        sys.exit(f"1Password lookup failed: {result.stderr.strip()}")

    blob = json.dumps(json.loads(result.stdout))
    ak_match, sk_match = ACCESS_KEY_RE.search(blob), SECRET_KEY_RE.search(blob)
    if not (ak_match and sk_match):
        sys.exit("Could not parse Onshape API keys from the 1Password item")
    return ak_match.group(0), sk_match.group(1)


def main():
    if not os.path.exists(VENV_PY):
        sys.exit(f"Missing venv at {VENV_PY} — run `uv sync` in {REPO}")

    ak, sk = resolve_keys()
    env = dict(os.environ, ONSHAPE_ACCESS_KEY=ak, ONSHAPE_SECRET_KEY=sk, PYTHONPATH=REPO)
    os.chdir(REPO)
    os.execve(VENV_PY, [VENV_PY, "-m", "onshape_mcp.server"], env)


if __name__ == "__main__":
    main()
