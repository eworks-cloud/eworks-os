"""Eworks OS — Click CLI entrypoint.

Commands:
  eworks auth login
  eworks auth status
  eworks campaign create / list / start / pause
  eworks prospect list / score
  eworks agent run / status
  eworks report daily
  eworks config set / show
  eworks daemon start / stop / status
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import click

from eworks.core.config import get_config
from eworks.core.database import DatabaseManager

# ─── Helpers ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _out(data: Any, as_json: bool = False) -> None:
    """Print data as JSON or formatted text."""
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, (dict, list)):
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            click.echo(str(data))


def _get_db() -> DatabaseManager:
    cfg = get_config()
    db = DatabaseManager(db_path=cfg.database_path)
    db.init_schema()
    return db


# ─── Root CLI ─────────────────────────────────────────────────────────────────


@click.group()
@click.version_option("0.1.0", prog_name="eworks")
def cli():
    """Eworks OS — Multi-Agent Company Operating System."""


# ─── auth ─────────────────────────────────────────────────────────────────────


@cli.group()
def auth():
    """LinkedIn authentication commands."""


@auth.command("login")
@click.option("--email", required=True, envvar="LINKEDIN_EMAIL", help="LinkedIn email")
@click.option("--password", required=True, envvar="LINKEDIN_PASSWORD", help="LinkedIn password", hide_input=True)
@click.option("--session-file", default="linkedin.json", help="Session file name")
@click.option("--json", "as_json", is_flag=True)
def auth_login(email: str, password: str, session_file: str, as_json: bool):
    """Log in to LinkedIn and save the session."""
    from eworks.agents.prospector.auth import LinkedInAuth

    cfg = get_config()
    auth_mgr = LinkedInAuth(
        session_dir=cfg.session_dir,
        user_agent=cfg.user_agent,
        viewport=cfg.viewport,
    )

    async def _run():
        success = await auth_mgr.login(email, password)
        if success:
            await auth_mgr.save_session(session_file)
        await auth_mgr.close()
        return success

    success = asyncio.run(_run())
    result = {"status": "logged_in" if success else "failed", "session_file": session_file}
    _out(result, as_json)
    sys.exit(0 if success else 1)


@auth.command("status")
@click.option("--session-file", default="linkedin.json")
@click.option("--json", "as_json", is_flag=True)
def auth_status(session_file: str, as_json: bool):
    """Check if the saved session is still valid."""
    from eworks.agents.prospector.auth import LinkedInAuth

    cfg = get_config()
    session_path = Path(cfg.session_dir) / session_file
    if not session_path.exists():
        _out({"status": "no_session", "file": str(session_path)}, as_json)
        return

    auth_mgr = LinkedInAuth(session_dir=cfg.session_dir, user_agent=cfg.user_agent, viewport=cfg.viewport)

    async def _run():
        await auth_mgr.load_session(session_file)
        logged_in = await auth_mgr.is_logged_in()
        await auth_mgr.close()
        return logged_in

    logged_in = asyncio.run(_run())
    _out({"status": "active" if logged_in else "expired", "file": str(session_path)}, as_json)


# ─── campaign ─────────────────────────────────────────────────────────────────


@cli.group()
def campaign():
    """Campaign management commands."""


@campaign.command("create")
@click.option("--name", required=True, help="Campaign name")
@click.option("--daily-limit", default=20, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def campaign_create(name: str, daily_limit: int, as_json: bool):
    """Create a new campaign."""
    db = _get_db()
    campaign_id = db.create_campaign({"name": name, "daily_limit": daily_limit, "status": "draft"})
    result = db.get_campaign(campaign_id)
    _out(dict(result), as_json)


@campaign.command("list")
@click.option("--json", "as_json", is_flag=True)
def campaign_list(as_json: bool):
    """List all campaigns."""
    db = _get_db()
    campaigns = db.list_campaigns()
    _out(campaigns, as_json)


@campaign.command("start")
@click.argument("campaign_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def campaign_start(campaign_id: int, as_json: bool):
    """Set a campaign to active status."""
    db = _get_db()
    db.update_campaign(campaign_id, {"status": "active"})
    result = db.get_campaign(campaign_id)
    _out(dict(result), as_json)


@campaign.command("pause")
@click.argument("campaign_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def campaign_pause(campaign_id: int, as_json: bool):
    """Pause a campaign."""
    db = _get_db()
    db.update_campaign(campaign_id, {"status": "paused"})
    result = db.get_campaign(campaign_id)
    _out(dict(result), as_json)


# ─── prospect ─────────────────────────────────────────────────────────────────


@cli.group()
def prospect():
    """Prospect management commands."""


@prospect.command("list")
@click.option("--campaign", "campaign_id", type=int, required=True)
@click.option("--status", default=None)
@click.option("--limit", default=50, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def prospect_list(campaign_id: int, status: str | None, limit: int, as_json: bool):
    """List prospects for a campaign."""
    db = _get_db()
    conn = db.get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM prospects WHERE campaign_id=? AND status=? LIMIT ?",
            (campaign_id, status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM prospects WHERE campaign_id=? LIMIT ?",
            (campaign_id, limit),
        ).fetchall()
    _out([dict(r) for r in rows], as_json)


@prospect.command("score")
@click.option("--campaign", "campaign_id", type=int, required=True)
@click.option("--json", "as_json", is_flag=True)
def prospect_score(campaign_id: int, as_json: bool):
    """Re-score all unscored prospects in a campaign."""
    from eworks.agents.prospector.discovery import ICPScorer

    db = _get_db()
    conn = db.get_connection()
    scorer = ICPScorer()
    rows = conn.execute(
        "SELECT * FROM prospects WHERE campaign_id=? AND status='discovered'",
        (campaign_id,),
    ).fetchall()
    updated = 0
    for row in rows:
        data = dict(row)
        result = scorer.score(data)
        conn.execute(
            "UPDATE prospects SET icp_score=?, icp_breakdown=?, status='scored' WHERE id=?",
            (result["score"], json.dumps(result["breakdown"]), data["id"]),
        )
        updated += 1
    conn.commit()
    _out({"updated": updated, "campaign_id": campaign_id}, as_json)


# ─── agent ────────────────────────────────────────────────────────────────────


@cli.group()
def agent():
    """Agent run commands."""


@agent.command("run")
@click.option("--campaign", "campaign_id", type=int, required=True)
@click.option("--dry-run", is_flag=True, help="Simulate without sending")
@click.option("--session-file", default="linkedin.json")
@click.option("--json", "as_json", is_flag=True)
def agent_run(campaign_id: int, dry_run: bool, session_file: str, as_json: bool):
    """Run the prospector agent for a campaign."""
    from eworks.agents.prospector.auth import LinkedInAuth
    from eworks.agents.prospector.executor import OutreachExecutor

    cfg = get_config()
    db = _get_db()

    if dry_run:
        _out({"status": "dry_run", "campaign_id": campaign_id, "message": "No actions taken"}, as_json)
        return

    auth_mgr = LinkedInAuth(session_dir=cfg.session_dir, user_agent=cfg.user_agent, viewport=cfg.viewport)
    executor = OutreachExecutor(daily_limit=cfg.daily_connection_limit)

    async def _run():
        await auth_mgr.load_session(session_file)
        if not await auth_mgr.is_logged_in():
            click.echo("ERROR: Not logged in. Run: eworks auth login first.", err=True)
            return {"error": "not_logged_in"}
        summary = await executor.run_campaign(auth_mgr, db, campaign_id)
        await auth_mgr.close()
        return summary

    result = asyncio.run(_run())
    _out(result, as_json)


@agent.command("status")
@click.option("--json", "as_json", is_flag=True)
def agent_status(as_json: bool):
    """Show recent agent run status."""
    db = _get_db()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT 10"
    ).fetchall()
    _out([dict(r) for r in rows], as_json)


# ─── report ───────────────────────────────────────────────────────────────────


@cli.group()
def report():
    """Reporting commands."""


@report.command("daily")
@click.option("--campaign", "campaign_id", type=int, required=True)
@click.option("--send/--no-send", default=True, help="Send via Telegram")
@click.option("--json", "as_json", is_flag=True)
def report_daily(campaign_id: int, send: bool, as_json: bool):
    """Generate and optionally send the daily report."""
    from eworks.agents.prospector.reporter import TelegramReporter

    cfg = get_config()
    db = _get_db()
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        _out({"error": f"Campaign {campaign_id} not found"}, as_json)
        return

    conn = db.get_connection()
    today_row = conn.execute(
        "SELECT * FROM agent_runs WHERE campaign_id=? ORDER BY started_at DESC LIMIT 1",
        (campaign_id,),
    ).fetchone()
    agent_run = dict(today_row) if today_row else {}

    if send:
        reporter = TelegramReporter(
            bot_token=cfg.telegram_bot_token,
            chat_id=cfg.telegram_chat_id,
        )
        asyncio.run(reporter.send_daily_report(agent_run, dict(campaign)))

    _out({"agent_run": agent_run, "campaign": dict(campaign)}, as_json)


# ─── config ───────────────────────────────────────────────────────────────────


@cli.group("config")
def config_group():
    """Configuration commands."""


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--json", "as_json", is_flag=True)
def config_set(key: str, value: str, as_json: bool):
    """Store a configuration value in the database."""
    db = _get_db()
    db.set_setting(key, value)
    _out({"key": key, "value": value, "status": "saved"}, as_json)


@config_group.command("show")
@click.option("--json", "as_json", is_flag=True)
def config_show(as_json: bool):
    """Show all configuration values from the database."""
    db = _get_db()
    conn = db.get_connection()
    rows = conn.execute("SELECT key, value, updated_at FROM settings_store ORDER BY key").fetchall()
    _out([dict(r) for r in rows], as_json)


# ─── daemon ───────────────────────────────────────────────────────────────────


@cli.group()
def daemon():
    """Daemon/scheduler process commands."""


_DAEMON_PID_FILE = Path("/tmp/eworks-daemon.pid")


@daemon.command("start")
@click.option("--json", "as_json", is_flag=True)
def daemon_start(as_json: bool):
    """Start the Eworks OS background scheduler daemon."""
    from eworks.core.scheduler import SchedulerManager

    if _DAEMON_PID_FILE.exists():
        pid = _DAEMON_PID_FILE.read_text().strip()
        _out({"status": "already_running", "pid": pid}, as_json)
        return

    scheduler = SchedulerManager()
    scheduler.start()
    _DAEMON_PID_FILE.write_text(str(os.getpid()))
    click.echo("Daemon started. Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        _DAEMON_PID_FILE.unlink(missing_ok=True)
        _out({"status": "stopped"}, as_json)


@daemon.command("stop")
@click.option("--json", "as_json", is_flag=True)
def daemon_stop(as_json: bool):
    """Stop the daemon (send SIGTERM to the daemon process)."""
    if not _DAEMON_PID_FILE.exists():
        _out({"status": "not_running"}, as_json)
        return
    import signal
    pid = int(_DAEMON_PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        _DAEMON_PID_FILE.unlink(missing_ok=True)
        _out({"status": "stopped", "pid": pid}, as_json)
    except ProcessLookupError:
        _DAEMON_PID_FILE.unlink(missing_ok=True)
        _out({"status": "was_not_running", "pid": pid}, as_json)


@daemon.command("status")
@click.option("--json", "as_json", is_flag=True)
def daemon_status(as_json: bool):
    """Show whether the daemon is running."""
    if not _DAEMON_PID_FILE.exists():
        _out({"status": "stopped"}, as_json)
        return
    pid = int(_DAEMON_PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        _out({"status": "running", "pid": pid}, as_json)
    except ProcessLookupError:
        _DAEMON_PID_FILE.unlink(missing_ok=True)
        _out({"status": "stale_pid_removed", "pid": pid}, as_json)


if __name__ == "__main__":
    cli()
