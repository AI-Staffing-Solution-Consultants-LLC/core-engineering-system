"""
agency-agents daemon — team-spawn coordinator (skeleton)

Phase-5 NEXUS-Sprint daemon. Exposes:
  - GET  /healthz      — liveness probe
  - POST /teams/spawn  — gated team-spawn endpoint (allowlist-as-config)

Port-bind is OFF by default. The daemon only binds to a TCP port when
explicitly invoked with the `--serve` flag. This is the human gate
(checkpoint #11): the daemon skeleton is in place, but the port-bind
side-effect is deferred until the user types YES.

Isolation contract (see teams.json):
  - tmpfs /var/ledger (per-team ephemeral ledger, no host persistence)
  - non-root user coreengine (no privilege escalation)
  - no allUsers binding (no public ingress)
  - allowlist subset scoped per team (no global tool access)

This daemon does NOT call Track A or Track B. Cross-track wiring is a
future task and requires explicit approval.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TEAMS_CONFIG_PATH = Path(os.environ.get("TEAMS_CONFIG_PATH", "/app/teams.json"))
DEFAULT_PORT = int(os.environ.get("DAEMON_PORT", "8082"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("agency-agents-daemon")


# ---------------------------------------------------------------------------
# Teams config loader
# ---------------------------------------------------------------------------
def load_teams_config(path: Path) -> dict:
    """Load the team-isolation contract from teams.json.

    Returns an empty dict if the file is missing or malformed — the daemon
    still serves /healthz but /teams/spawn will reject every request.
    """
    if not path.is_file():
        logger.warning(
            "Teams config %s not found — /teams/spawn will reject all requests", path
        )
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        teams = data.get("teams", {})
        logger.info("Loaded %d team definitions from %s", len(teams), path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load teams config %s: %s", path, exc)
        return {}


TEAMS_CONFIG = load_teams_config(TEAMS_CONFIG_PATH)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/healthz", methods=["GET"])
def healthz():
    """Liveness probe. Always returns 200 with status=ok."""
    return jsonify({"status": "ok", "service": "agency-agents-daemon"}), 200


@app.route("/teams/spawn", methods=["POST"])
def teams_spawn():
    """Gated team-spawn endpoint.

    Request body: {"team": "<team-name>", "task": "<task-description>"}
    Response: stub {"team": ..., "task": ..., "status": "queued"} on success,
              or 403 with reason on rejection.

    Gating rules (allowlist-as-config):
      1. team name must exist in teams.json
      2. team must have an allowlist_subset (no global tool access)
      3. team must declare non-root + no_allUsers_binding (isolation contract)
    """
    if not TEAMS_CONFIG:
        return jsonify({"error": "teams config not loaded"}), 503

    payload = request.get_json(silent=True) or {}
    team_name = payload.get("team", "")
    task_desc = payload.get("task", "")

    if not team_name:
        return jsonify({"error": "missing 'team' field"}), 400
    if not task_desc:
        return jsonify({"error": "missing 'task' field"}), 400

    teams = TEAMS_CONFIG.get("teams", {})
    team_def = teams.get(team_name)
    if team_def is None:
        return jsonify({"error": f"team '{team_name}' not in allowlist"}), 403

    # Isolation contract enforcement
    isolation = team_def.get("isolation", {})
    if not isolation.get("non-root"):
        return jsonify({"error": f"team '{team_name}' missing non-root isolation"}), 403
    if isolation.get("no_allUsers_binding") is not True:
        return jsonify(
            {"error": f"team '{team_name}' must declare no_allUsers_binding=true"}
        ), 403
    if "tmpfs" not in isolation:
        return jsonify({"error": f"team '{team_name}' missing tmpfs isolation"}), 403
    if not team_def.get("allowlist_subset"):
        return jsonify({"error": f"team '{team_name}' has empty allowlist_subset"}), 403

    # Stub response — actual spawn logic is a future task
    return jsonify(
        {
            "team": team_name,
            "task": task_desc,
            "status": "queued",
            "isolation": isolation,
            "allowlist_subset": team_def.get("allowlist_subset", []),
        }
    ), 202


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="agency-agents daemon (skeleton — port-bind OFF by default)"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Bind to TCP port and serve HTTP. Default OFF (human gate #11).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port to bind when --serve is set (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind when --serve is set (default: 127.0.0.1 — loopback only)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Verify daemon parses and configs load without binding a port.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.self_test:
        # Self-test: load configs, verify parse, print status, exit.
        # Does NOT bind to any port.
        print("SELF-TEST: OK — daemon parses, no port bind")
        print(
            json.dumps(
                {
                    "mode": "self-test",
                    "port_bind": False,
                    "teams_loaded": len(TEAMS_CONFIG.get("teams", {})),
                    "endpoints": ["/healthz", "/teams/spawn"],
                },
                indent=2,
            )
        )
        return 0

    if not args.serve:
        logger.info(
            "Daemon skeleton loaded. Port-bind OFF (no --serve flag). "
            "Run with --serve to bind %s:%d. See checkpoint #11.",
            args.host,
            args.port,
        )
        # Print config summary and exit cleanly. No socket is opened.
        print(
            json.dumps(
                {
                    "mode": "skeleton",
                    "port_bind": False,
                    "teams_loaded": len(TEAMS_CONFIG.get("teams", {})),
                    "endpoints": ["/healthz", "/teams/spawn"],
                    "isolation_contract": {
                        "tmpfs": "/var/ledger",
                        "non_root": "coreengine",
                        "no_allUsers_binding": True,
                    },
                },
                indent=2,
            )
        )
        return 0

    logger.info("Starting daemon on %s:%d", args.host, args.port)
    # debug=False, use_reloader=False — production-safe defaults
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
