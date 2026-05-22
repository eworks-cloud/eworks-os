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

import phoenix as px # Added for Phoenix
import click
from datetime import datetime

from eworks.core.config import get_config
from eworks.core.database import DatabaseManager

# ─── Helpers ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Phoenix AI Observability Initialization ──────────────────────────────────
try:
    PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "").strip()
    PHOENIX_BASE_URL = os.getenv("PHOENIX_BASE_URL", "https://app.arize.com/api/phoenix/v1").strip()
    
    if PHOENIX_API_KEY:
        px.init(api_key=PHOENIX_API_KEY, base_url=PHOENIX_BASE_URL)
        logger.info("✓ Phoenix AI Observability initialized for Eworks OS agents.")
    else:
        logger.debug("Phoenix API key not configured; observability disabled.")
except Exception as e:
    logger.warning(f"Phoenix initialization failed (non-blocking): {e}")


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
@click.version_option("0.1.0", prog_name="eos")
def cli():
    """EOS — Eworks OS Multi-Agent Company Operating System."""


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


# ─── proposal ─────────────────────────────────────────────────────────────────


@cli.group()
def proposal():
    """Proposal generation and management commands."""


@proposal.command("new")
@click.option("--client", "client_name", required=True, help="Client full name")
@click.option("--company", default="", help="Client company name")
@click.option("--notes-file", "notes_file", required=True, type=click.Path(exists=True), help="Path to discovery notes file")
@click.option("--no-deliver", is_flag=True, help="Skip Telegram delivery")
@click.option("--json", "as_json", is_flag=True)
def proposal_new(client_name: str, company: str, notes_file: str, no_deliver: bool, as_json: bool):
    """Generate a new proposal from discovery call notes."""
    from eworks.agents.closer.orchestrator import CloserOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()

    notes = Path(notes_file).read_text(encoding="utf-8")
    orchestrator = CloserOrchestrator(db=db, config=cfg)

    result = asyncio.run(orchestrator.run_from_notes(
        client_name=client_name,
        company=company,
        notes=notes,
        deliver=not no_deliver,
    ))
    _out(result, as_json)


@proposal.command("list")
@click.option("--status", default=None, help="Filter by status (draft/sent/accepted/rejected)")
@click.option("--json", "as_json", is_flag=True)
def proposal_list(status: str | None, as_json: bool):
    """List all proposals."""
    db = _get_db()
    db.add_closer_tables()
    conn = db.get_connection()
    if status:
        rows = conn.execute(
            "SELECT p.*, c.name as client_name, c.company FROM proposals p "
            "LEFT JOIN clients c ON c.id=p.client_id WHERE p.status=? ORDER BY p.created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT p.*, c.name as client_name, c.company FROM proposals p "
            "LEFT JOIN clients c ON c.id=p.client_id ORDER BY p.created_at DESC"
        ).fetchall()
    _out([dict(r) for r in rows], as_json)


@proposal.command("show")
@click.argument("proposal_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def proposal_show(proposal_id: int, as_json: bool):
    """Show full details for a proposal."""
    db = _get_db()
    db.add_closer_tables()
    conn = db.get_connection()
    row = conn.execute(
        "SELECT p.*, c.name as client_name, c.company, c.email FROM proposals p "
        "LEFT JOIN clients c ON c.id=p.client_id WHERE p.id=?",
        (proposal_id,),
    ).fetchone()
    if not row:
        _out({"error": f"Proposal {proposal_id} not found"}, as_json)
        return
    _out(dict(row), as_json)


@proposal.command("deliver")
@click.argument("proposal_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def proposal_deliver(proposal_id: int, as_json: bool):
    """Deliver a proposal via Telegram."""
    from eworks.agents.closer.delivery import ProposalDelivery

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    delivery = ProposalDelivery(db=db, config=cfg)
    sent = asyncio.run(delivery.deliver_via_telegram(proposal_id))
    _out({"proposal_id": proposal_id, "delivered": sent}, as_json)


@proposal.command("accept")
@click.argument("proposal_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def proposal_accept(proposal_id: int, as_json: bool):
    """Mark a proposal as accepted."""
    from eworks.agents.closer.delivery import ProposalDelivery

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    delivery = ProposalDelivery(db=db, config=cfg)
    ok = asyncio.run(delivery.mark_accepted(proposal_id))
    _out({"proposal_id": proposal_id, "accepted": ok}, as_json)


@proposal.command("reject")
@click.argument("proposal_id", type=int)
@click.option("--reason", default=None, help="Rejection reason")
@click.option("--json", "as_json", is_flag=True)
def proposal_reject(proposal_id: int, reason: str | None, as_json: bool):
    """Mark a proposal as rejected."""
    from eworks.agents.closer.delivery import ProposalDelivery

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    delivery = ProposalDelivery(db=db, config=cfg)
    ok = asyncio.run(delivery.mark_rejected(proposal_id, reason=reason))
    _out({"proposal_id": proposal_id, "rejected": ok, "reason": reason}, as_json)


@proposal.command("pipeline")
@click.option("--json", "as_json", is_flag=True)
def proposal_pipeline(as_json: bool):
    """Show proposal pipeline summary (counts + value by status)."""
    from eworks.agents.closer.delivery import ProposalDelivery

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    delivery = ProposalDelivery(db=db, config=cfg)
    summary = asyncio.run(delivery.get_pipeline_summary())
    _out(summary, as_json)


# ─── publish ──────────────────────────────────────────────────────────────────


@cli.group()
def publish():
    """Content pipeline publishing commands."""


@publish.command("run")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), show_default=True, help="Content language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval step")
@click.option("--json", "as_json", is_flag=True)
def publish_run(language: str, auto_approve: bool, as_json: bool):
    """Run the full content pipeline: ideation → scripting → video → publish."""
    from eworks.agents.publisher.orchestrator import PublisherOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_publisher_tables()
    orchestrator = PublisherOrchestrator(db=db, config=cfg)

    async def _run():
        return await orchestrator.run(language=language, auto_approve=auto_approve)

    result = asyncio.run(_run())
    _out(result, as_json)


@publish.command("ideas")
@click.option("--n", default=5, show_default=True, help="Number of ideas to generate")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), show_default=True)
@click.option("--niche", default="AI automation for businesses", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def publish_ideas(n: int, language: str, niche: str, as_json: bool):
    """Generate content ideas using Claude AI."""
    from eworks.agents.publisher.ideation import IdeationAgent

    cfg = get_config()
    db = _get_db()
    db.add_publisher_tables()
    agent = IdeationAgent(db=db, config=cfg)

    async def _run():
        return await agent.generate_ideas(n=n, language=language, niche=niche)

    ideas = asyncio.run(_run())
    _out(ideas, as_json)


@publish.command("status")
@click.option("--json", "as_json", is_flag=True)
def publish_status(as_json: bool):
    """Show status of all content posts."""
    db = _get_db()
    db.add_publisher_tables()
    posts = db.list_content_posts(limit=20)
    ideas = db.list_content_ideas(limit=20)
    _out({"posts": posts, "ideas": ideas}, as_json)


@publish.command("approve")
@click.argument("post_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def publish_approve(post_id: int, as_json: bool):
    """Manually approve a content post for publishing."""
    db = _get_db()
    db.add_publisher_tables()
    post = db.get_content_post(post_id)
    if not post:
        _out({"error": f"Post {post_id} not found"}, as_json)
        sys.exit(1)
    db.update_content_post(post_id, {"status": "approved"})
    result = db.get_content_post(post_id)
    _out(dict(result), as_json)


@publish.command("reject")
@click.argument("post_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def publish_reject(post_id: int, as_json: bool):
    """Manually reject a content post."""
    db = _get_db()
    db.add_publisher_tables()
    post = db.get_content_post(post_id)
    if not post:
        _out({"error": f"Post {post_id} not found"}, as_json)
        sys.exit(1)
    db.update_content_post(post_id, {"status": "failed"})
    result = db.get_content_post(post_id)
    _out(dict(result), as_json)


# ─── project ──────────────────────────────────────────────────────────────────


@cli.group()
def project():
    """Project management commands."""


@project.command("create")
@click.option("--client", "client_id", required=True, type=int, help="Client ID")
@click.option("--name", required=True, help="Project name")
@click.option("--budget", default=0.0, type=float, help="Total project budget")
@click.option("--start", "start_date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", "end_date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--proposal", "proposal_id", default=None, type=int, help="Linked proposal ID")
@click.option("--rate", "hourly_rate", default=150.0, type=float, help="Hourly rate")
@click.option("--json", "as_json", is_flag=True)
def project_create(client_id, name, budget, start_date, end_date, proposal_id, hourly_rate, as_json):
    """Create a new project."""
    from eworks.agents.conductor.tracker import ProjectTracker

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    tracker = ProjectTracker(db=db, config=cfg)
    pid = tracker.create_project(
        client_id=client_id,
        proposal_id=proposal_id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        hourly_rate=hourly_rate,
    )
    summary = tracker.get_project_summary(pid)
    _out(summary, as_json)


@project.command("list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--json", "as_json", is_flag=True)
def project_list(status, as_json):
    """List projects."""
    db = _get_db()
    db.add_conductor_tables()
    conn = db.get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM projects WHERE status=? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    _out([dict(r) for r in rows], as_json)


@project.command("status")
@click.argument("project_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def project_status(project_id, as_json):
    """Show project summary and health score."""
    from eworks.agents.conductor.tracker import ProjectTracker

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    tracker = ProjectTracker(db=db, config=cfg)
    summary = tracker.get_project_summary(project_id)
    if not summary:
        _out({"error": f"Project {project_id} not found"}, as_json)
        sys.exit(1)
    _out(summary, as_json)


@project.command("log-hours")
@click.argument("project_id", type=int)
@click.option("--task", "task_id", default=None, type=int, help="Task ID")
@click.option("--hours", required=True, type=float, help="Hours to log")
@click.option("--note", default="", help="Description")
@click.option("--json", "as_json", is_flag=True)
def project_log_hours(project_id, task_id, hours, note, as_json):
    """Log hours to a project."""
    from eworks.agents.conductor.tracker import ProjectTracker

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    tracker = ProjectTracker(db=db, config=cfg)
    ok = tracker.log_hours(project_id, task_id, hours, note)
    _out({"logged": ok, "project_id": project_id, "hours": hours}, as_json)


# ─── sprint ────────────────────────────────────────────────────────────────────


@cli.group()
def sprint():
    """Sprint management commands."""


@sprint.command("create")
@click.option("--project", "project_id", required=True, type=int)
@click.option("--name", required=True)
@click.option("--goal", default="")
@click.option("--start", "start_date", default=None)
@click.option("--end", "end_date", default=None)
@click.option("--json", "as_json", is_flag=True)
def sprint_create(project_id, name, goal, start_date, end_date, as_json):
    """Create a sprint for a project."""
    from eworks.agents.conductor.sprint_manager import SprintManager

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    mgr = SprintManager(db=db, config=cfg)
    sid = mgr.create_sprint(project_id, name, goal, start_date, end_date)
    _out({"sprint_id": sid, "project_id": project_id, "name": name}, as_json)


@sprint.command("board")
@click.argument("sprint_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def sprint_board(sprint_id, as_json):
    """Show the Kanban board for a sprint."""
    from eworks.agents.conductor.sprint_manager import SprintManager

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    mgr = SprintManager(db=db, config=cfg)
    board = mgr.get_sprint_board(sprint_id)
    velocity = mgr.get_sprint_velocity(sprint_id)
    _out({"sprint_id": sprint_id, "velocity": velocity, "board": board}, as_json)


# ─── task ──────────────────────────────────────────────────────────────────────


@cli.group()
def task():
    """Task management commands."""


@task.command("add")
@click.option("--sprint", "sprint_id", required=True, type=int)
@click.option("--title", required=True)
@click.option("--points", "story_points", default=1, type=int)
@click.option("--priority", default="medium", type=click.Choice(["critical", "high", "medium", "low"]))
@click.option("--assignee", default="AI Agent")
@click.option("--due", "due_date", default=None)
@click.option("--json", "as_json", is_flag=True)
def task_add(sprint_id, title, story_points, priority, assignee, due_date, as_json):
    """Add a task to a sprint."""
    from eworks.agents.conductor.sprint_manager import SprintManager

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    mgr = SprintManager(db=db, config=cfg)
    tid = mgr.add_task(sprint_id, title, priority=priority, story_points=story_points, assignee=assignee, due_date=due_date)
    _out({"task_id": tid, "sprint_id": sprint_id, "title": title}, as_json)


@task.command("update")
@click.argument("task_id", type=int)
@click.option("--status", required=True, type=click.Choice(["backlog", "todo", "in_progress", "review", "done", "cancelled"]))
@click.option("--json", "as_json", is_flag=True)
def task_update(task_id, status, as_json):
    """Update a task's status."""
    from eworks.agents.conductor.sprint_manager import SprintManager

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    mgr = SprintManager(db=db, config=cfg)
    ok = mgr.update_task_status(task_id, status)
    _out({"task_id": task_id, "status": status, "updated": ok}, as_json)


# ─── conductor ────────────────────────────────────────────────────────────────


@cli.group()
def conductor():
    """Conductor agent commands."""


@conductor.command("daily-check")
@click.option("--json", "as_json", is_flag=True)
def conductor_daily_check(as_json):
    """Run daily health check across all active projects."""
    from eworks.agents.conductor.orchestrator import ConductorOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    orch = ConductorOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.run_daily_check())
    _out(result, as_json)


@conductor.command("weekly-reports")
@click.option("--json", "as_json", is_flag=True)
def conductor_weekly_reports(as_json):
    """Generate and send weekly reports for all active projects."""
    from eworks.agents.conductor.orchestrator import ConductorOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_conductor_tables()
    orch = ConductorOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.run_weekly_reports())
    _out(result, as_json)


# ─── invoice ──────────────────────────────────────────────────────────────────


@cli.group()
def invoice():
    """Invoice generation and billing commands."""


@invoice.command("create")
@click.option("--client", "client_id", required=True, type=int, help="Client ID")
@click.option("--project", "project_id", default=None, type=int, help="Project ID")
@click.option("--item", "raw_items", multiple=True, help='Item as "desc:qty:unit_price" (repeat for multiple)')
@click.option("--due-days", default=30, show_default=True, type=int, help="Days until due")
@click.option("--tax-rate", default=0.0, type=float, help="Tax rate percentage (e.g. 10.0)")
@click.option("--notes", default=None, help="Invoice notes")
@click.option("--json", "as_json", is_flag=True)
def invoice_create(client_id, project_id, raw_items, due_days, tax_rate, notes, as_json):
    """Create a new invoice for a client."""
    from eworks.agents.treasurer.invoice_generator import InvoiceGenerator

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()

    # Parse items
    items = []
    for raw in raw_items:
        parts = raw.split(":")
        if len(parts) != 3:
            click.echo(f"ERROR: Item format must be 'description:quantity:unit_price', got: {raw}", err=True)
            sys.exit(1)
        desc, qty, price = parts
        items.append({"description": desc.strip(), "quantity": float(qty), "unit_price": float(price)})

    if not items:
        # Default placeholder item
        items = [{"description": "Professional Services", "quantity": 1, "unit_price": 0.0}]

    gen = InvoiceGenerator(db=db, config=cfg)
    invoice_id = gen.create_invoice(
        client_id=client_id,
        project_id=project_id,
        items=items,
        due_days=due_days,
        notes=notes,
        tax_rate=tax_rate,
    )
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    _out(dict(row), as_json)


@invoice.command("list")
@click.option("--status", default=None, help="Filter by status (draft/sent/paid/overdue)")
@click.option("--json", "as_json", is_flag=True)
def invoice_list(status, as_json):
    """List invoices, optionally filtered by status."""
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    conn = db.get_connection()
    if status:
        rows = conn.execute(
            """SELECT i.*, c.name as client_name FROM invoices i
               LEFT JOIN clients c ON c.id=i.client_id
               WHERE i.status=? ORDER BY i.created_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT i.*, c.name as client_name FROM invoices i
               LEFT JOIN clients c ON c.id=i.client_id
               ORDER BY i.created_at DESC"""
        ).fetchall()
    _out([dict(r) for r in rows], as_json)


@invoice.command("show")
@click.argument("invoice_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def invoice_show(invoice_id, as_json):
    """Show full details for an invoice, including line items."""
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    conn = db.get_connection()
    row = conn.execute(
        """SELECT i.*, c.name as client_name, c.company, c.email
           FROM invoices i LEFT JOIN clients c ON c.id=i.client_id
           WHERE i.id=?""",
        (invoice_id,),
    ).fetchone()
    if not row:
        _out({"error": f"Invoice {invoice_id} not found"}, as_json)
        sys.exit(1)
    inv = dict(row)
    items = conn.execute(
        "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (invoice_id,)
    ).fetchall()
    inv["items"] = [dict(i) for i in items]
    _out(inv, as_json)


@invoice.command("send")
@click.argument("invoice_id", type=int)
@click.option("--json", "as_json", is_flag=True)
def invoice_send(invoice_id, as_json):
    """Mark an invoice as 'sent' (update status)."""
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        _out({"error": f"Invoice {invoice_id} not found"}, as_json)
        sys.exit(1)
    conn.execute("UPDATE invoices SET status='sent' WHERE id=?", (invoice_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    _out(dict(row), as_json)


@invoice.command("mark-paid")
@click.argument("invoice_id", type=int)
@click.option("--amount", required=True, type=float, help="Amount paid")
@click.option("--method", default=None, help="Payment method (wire/card/crypto/etc.)")
@click.option("--reference", default=None, help="Payment reference number")
@click.option("--date", "payment_date", default=None, help="Payment date (YYYY-MM-DD, default: today)")
@click.option("--json", "as_json", is_flag=True)
def invoice_mark_paid(invoice_id, amount, method, reference, payment_date, as_json):
    """Record a payment against an invoice."""
    from eworks.agents.treasurer.payment_tracker import PaymentTracker
    from datetime import date

    if not payment_date:
        payment_date = date.today().isoformat()

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    tracker = PaymentTracker(db=db, config=cfg)
    payment_id = tracker.record_payment(invoice_id, amount, payment_date, method, reference)
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    _out({"payment_id": payment_id, "invoice": dict(row)}, as_json)


@invoice.command("revenue")
@click.option("--period", default="month", type=click.Choice(["month", "quarter", "year"]), show_default=True)
@click.option("--json", "as_json", is_flag=True)
def invoice_revenue(period, as_json):
    """Show revenue summary for a period."""
    from eworks.agents.treasurer.payment_tracker import PaymentTracker

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    tracker = PaymentTracker(db=db, config=cfg)
    summary = tracker.get_revenue_summary(period=period)
    _out(summary, as_json)


# ─── treasurer ────────────────────────────────────────────────────────────────


@cli.group()
def treasurer():
    """Treasurer agent commands."""


@treasurer.command("daily")
@click.option("--json", "as_json", is_flag=True)
def treasurer_daily(as_json):
    """Run the daily treasurer workflow: mark overdue, send reminders, report."""
    from eworks.agents.treasurer.orchestrator import TreasurerOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_treasurer_tables()
    orch = TreasurerOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.run_daily())
    _out(result, as_json)


# ─── onboard ──────────────────────────────────────────────────────────────────


@cli.group()
def onboard():
    """Client onboarding commands."""


@onboard.command("create")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--project", "project_id", type=int, default=None, help="Project ID (optional)")
@click.option("--json", "as_json", is_flag=True)
def onboard_create(client_id: int, project_id: int | None, as_json: bool):
    """Create a 7-step onboarding checklist for a client."""
    from eworks.agents.nurturer.onboarding import OnboardingManager

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    mgr = OnboardingManager(db=db, config=cfg)
    count = mgr.create_onboarding(client_id, project_id=project_id)
    _out({"client_id": client_id, "steps_created": count}, as_json)


@onboard.command("status")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--json", "as_json", is_flag=True)
def onboard_status(client_id: int, as_json: bool):
    """Show onboarding progress for a client."""
    from eworks.agents.nurturer.onboarding import OnboardingManager

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    mgr = OnboardingManager(db=db, config=cfg)
    result = mgr.get_onboarding_progress(client_id)
    _out(result, as_json)


@onboard.command("complete")
@click.argument("step_id", type=int)
@click.option("--notes", default=None, help="Completion notes")
@click.option("--json", "as_json", is_flag=True)
def onboard_complete(step_id: int, notes: str | None, as_json: bool):
    """Mark an onboarding checklist step as completed."""
    from eworks.agents.nurturer.onboarding import OnboardingManager

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    mgr = OnboardingManager(db=db, config=cfg)
    ok = mgr.complete_step(step_id, notes=notes)
    _out({"step_id": step_id, "completed": ok}, as_json)


# ─── health ───────────────────────────────────────────────────────────────────


@cli.group()
def health():
    """Client health score commands."""


@health.command("score")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--json", "as_json", is_flag=True)
def health_score(client_id: int, as_json: bool):
    """Calculate and record a health score for a client."""
    from eworks.agents.nurturer.health_scorer import HealthScorer

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    scorer = HealthScorer(db=db, config=cfg)
    score = scorer.record_health_score(client_id)
    _out({"client_id": client_id, "health_score": score}, as_json)


@health.command("trend")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--n", "last_n", type=int, default=5, show_default=True, help="Number of records")
@click.option("--json", "as_json", is_flag=True)
def health_trend(client_id: int, last_n: int, as_json: bool):
    """Show health score trend for a client."""
    from eworks.agents.nurturer.health_scorer import HealthScorer

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    scorer = HealthScorer(db=db, config=cfg)
    trend = scorer.get_health_trend(client_id, last_n=last_n)
    _out(trend, as_json)


@health.command("at-risk")
@click.option("--json", "as_json", is_flag=True)
def health_at_risk(as_json: bool):
    """List clients with health scores below 60."""
    from eworks.agents.nurturer.health_scorer import HealthScorer

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    scorer = HealthScorer(db=db, config=cfg)
    at_risk = scorer.get_at_risk_clients()
    _out(at_risk, as_json)


# ─── upsell ───────────────────────────────────────────────────────────────────


@cli.group()
def upsell():
    """Upsell opportunity commands."""


@upsell.command("detect")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--json", "as_json", is_flag=True)
def upsell_detect(client_id: int, as_json: bool):
    """Use Claude AI to detect upsell opportunities for a client."""
    from eworks.agents.nurturer.upsell_detector import UpsellDetector

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    detector = UpsellDetector(db=db, config=cfg)
    results = asyncio.run(detector.detect_opportunities(client_id))
    _out(results, as_json)


@upsell.command("pipeline")
@click.option("--json", "as_json", is_flag=True)
def upsell_pipeline(as_json: bool):
    """Show upsell pipeline value by confidence level."""
    from eworks.agents.nurturer.upsell_detector import UpsellDetector

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    detector = UpsellDetector(db=db, config=cfg)
    pipeline = detector.get_pipeline_value()
    _out(pipeline, as_json)


# ─── checkin ──────────────────────────────────────────────────────────────────


@cli.group()
def checkin():
    """Client check-in commands."""


@checkin.command("send")
@click.option("--client", "client_id", type=int, required=True, help="Client ID")
@click.option("--type", "checkin_type", default="monthly", show_default=True,
              type=click.Choice(["weekly", "monthly", "quarterly", "ad_hoc"]),
              help="Check-in type")
@click.option("--json", "as_json", is_flag=True)
def checkin_send(client_id: int, checkin_type: str, as_json: bool):
    """Send an AI-personalized check-in to a client."""
    from eworks.agents.nurturer.checkin_system import CheckinSystem

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    system = CheckinSystem(db=db, config=cfg)
    checkin_id = asyncio.run(system.send_checkin(client_id, checkin_type=checkin_type))
    _out({"client_id": client_id, "checkin_id": checkin_id, "type": checkin_type}, as_json)


# ─── nurturer ─────────────────────────────────────────────────────────────────


@cli.group()
def nurturer():
    """Customer Success Agent (Nurturer) commands."""


@nurturer.command("daily")
@click.option("--json", "as_json", is_flag=True)
def nurturer_daily(as_json: bool):
    """Run the daily customer success pipeline: score, alert, check-in."""
    from eworks.agents.nurturer.orchestrator import NurturerOrchestrator

    cfg = get_config()
    db = _get_db()
    db.add_closer_tables()
    db.add_nurturer_tables()
    orch = NurturerOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.run_daily())
    _out(result, as_json)


# ─── social ───────────────────────────────────────────────────────────────────


@cli.group()
def social():
    """Social media publishing commands (LinkedIn + Instagram)."""


def _get_social_db():
    """Get DB with all social publisher tables initialized."""
    db = _get_db()
    db.add_publisher_tables()
    db.add_social_publisher_tables()
    return db


def _resolve_platforms(platform: str) -> list[str]:
    """Resolve 'both' to list of platforms."""
    if platform == "both":
        return ["linkedin", "instagram"]
    return [platform]


@social.command("post")
@click.option("--platform", default="both", type=click.Choice(["linkedin", "instagram", "both"]), help="Target platform")
@click.option("--type", "content_type", default="image", type=click.Choice(["text", "image", "video", "carousel"]), help="Content type")
@click.option("--topic", default=None, help="Specific topic (optional — AI generates if omitted)")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Content language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Preview without posting")
@click.option("--json", "as_json", is_flag=True)
def social_post(platform, content_type, topic, language, auto_approve, dry_run, as_json):
    """Generate and post content to social media."""
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator

    cfg = get_config()
    db = _get_social_db()
    orch = SocialOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.post_content(
        platforms=_resolve_platforms(platform),
        content_type=content_type,
        language=language,
        topic=topic,
        auto_approve=auto_approve,
        dry_run=dry_run,
    ))
    _out(result, as_json)


@social.command("text")
@click.option("--platform", default="linkedin", type=click.Choice(["linkedin", "instagram", "both"]))
@click.option("--topic", required=True)
@click.option("--language", default="en", type=click.Choice(["en", "pt"]))
@click.option("--auto-approve", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def social_text(platform, topic, language, auto_approve, as_json):
    """Post a text-only post (LinkedIn preferred)."""
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator

    cfg = get_config()
    db = _get_social_db()
    orch = SocialOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.post_content(
        platforms=_resolve_platforms(platform),
        content_type="text",
        language=language,
        topic=topic,
        auto_approve=auto_approve,
    ))
    _out(result, as_json)


@social.command("image")
@click.option("--platform", default="both", type=click.Choice(["linkedin", "instagram", "both"]))
@click.option("--topic", required=True)
@click.option("--language", default="en", type=click.Choice(["en", "pt"]))
@click.option("--auto-approve", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def social_image(platform, topic, language, auto_approve, as_json):
    """Generate AI image and post to social media."""
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator

    cfg = get_config()
    db = _get_social_db()
    orch = SocialOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.post_content(
        platforms=_resolve_platforms(platform),
        content_type="image",
        language=language,
        topic=topic,
        auto_approve=auto_approve,
    ))
    _out(result, as_json)


@social.command("video")
@click.option("--platform", default="both", type=click.Choice(["linkedin", "instagram", "both"]))
@click.option("--language", default="en", type=click.Choice(["en", "pt"]))
@click.option("--auto-approve", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def social_video(platform, language, auto_approve, as_json):
    """Generate HeyGen avatar video and post."""
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator

    cfg = get_config()
    db = _get_social_db()
    orch = SocialOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.post_content(
        platforms=_resolve_platforms(platform),
        content_type="video",
        language=language,
        auto_approve=auto_approve,
    ))
    _out(result, as_json)


@social.command("carousel")
@click.option("--platform", default="both", type=click.Choice(["linkedin", "instagram", "both"]))
@click.option("--topic", required=True)
@click.option("--slides", default=4, help="Number of slides (max 9 LinkedIn, 10 Instagram)")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]))
@click.option("--auto-approve", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def social_carousel(platform, topic, slides, language, auto_approve, as_json):
    """Generate multi-image carousel and post."""
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator

    cfg = get_config()
    db = _get_social_db()
    orch = SocialOrchestrator(db=db, config=cfg)
    result = asyncio.run(orch.post_content(
        platforms=_resolve_platforms(platform),
        content_type="carousel",
        language=language,
        topic=topic,
        auto_approve=auto_approve,
    ))
    _out(result, as_json)


@social.command("analytics")
@click.option("--post-id", type=int, required=True)
@click.option("--json", "as_json", is_flag=True)
def social_analytics(post_id, as_json):
    """Fetch analytics for a social post."""
    from eworks.agents.publisher.analytics import AnalyticsCollector

    db = _get_social_db()
    collector = AnalyticsCollector(db)
    # Get post details from DB
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM social_posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        click.echo(f"Post {post_id} not found.", err=True)
        return
    post = dict(row)
    results = {"post_id": post_id, "platform": post.get("platform"), "analytics": {}}
    if post.get("linkedin_post_urn"):
        results["analytics"]["linkedin"] = collector.collect_linkedin(post_id, post["linkedin_post_urn"])
    if post.get("instagram_post_id"):
        results["analytics"]["instagram"] = asyncio.run(
            collector.collect_instagram(post_id, post["instagram_post_id"])
        )
    _out(results, as_json)


@social.command("list")
@click.option("--platform", default=None)
@click.option("--status", default=None)
@click.option("--limit", default=20, type=int)
@click.option("--json", "as_json", is_flag=True)
def social_list(platform, status, limit, as_json):
    """List all social posts."""
    db = _get_social_db()
    conn = db.get_connection()
    query = "SELECT * FROM social_posts WHERE 1=1"
    params = []
    if platform:
        query += " AND platform LIKE ?"
        params.append(f"%{platform}%")
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    posts = [dict(r) for r in rows]
    _out(posts, as_json)


@social.command("schedule")
@click.option("--platform", default="both", type=click.Choice(["linkedin", "instagram", "both"]))
@click.option("--type", "content_type", default="image", type=click.Choice(["text", "image", "video", "carousel"]))
@click.option("--cron", default="0 9 * * 2,3,4", help="Cron expression (default: Tue-Thu 9 AM)")
@click.option("--json", "as_json", is_flag=True)
def social_schedule(platform, content_type, cron, as_json):
    """Schedule recurring social media posts (shows cron config to register)."""
    info = {
        "platforms": _resolve_platforms(platform),
        "content_type": content_type,
        "cron": cron,
        "message": (
            f"To schedule, add a cron job running: "
            f"eworks social post --platform {platform} --type {content_type} --auto-approve"
        ),
        "optimal_times": "Tue-Thu (days 2,3,4) at 9 AM",
    }
    _out(info, as_json)


# ─── x (X.com / Twitter) ─────────────────────────────────────────────────────


@cli.group()
def x():
    """X.com (Twitter) publishing commands."""


def _get_x_orchestrator():
    """Instantiate XOrchestrator with DB + config."""
    from eworks.agents.publisher.x_orchestrator import XOrchestrator
    db = _get_db()
    db.add_x_publisher_tables()
    cfg = get_config()
    return XOrchestrator(db, cfg)


@x.command("tweet")
@click.option("--topic", required=True, help="Tweet topic or content brief")
@click.option(
    "--style",
    default="insight",
    type=click.Choice(["insight", "tip", "question", "stat", "announcement"]),
    help="Tweet style",
)
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Generate without posting")
@click.option("--json", "as_json", is_flag=True)
def x_tweet(topic, style, language, auto_approve, dry_run, as_json):
    """Generate and post a single tweet."""
    orch = _get_x_orchestrator()
    result = asyncio.run(
        orch.post(
            content_type="tweet",
            topic=topic,
            language=language,
            style=style,
            auto_approve=auto_approve,
            dry_run=dry_run,
        )
    )
    _out(result, as_json)


@x.command("thread")
@click.option("--topic", required=True, help="Thread topic")
@click.option("--length", default=5, type=int, help="Number of tweets in thread")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Generate without posting")
@click.option("--json", "as_json", is_flag=True)
def x_thread(topic, length, language, auto_approve, dry_run, as_json):
    """Generate and post a tweet thread."""
    orch = _get_x_orchestrator()
    result = asyncio.run(
        orch.post(
            content_type="thread",
            topic=topic,
            language=language,
            thread_length=length,
            auto_approve=auto_approve,
            dry_run=dry_run,
        )
    )
    _out(result, as_json)


@x.command("image")
@click.option("--topic", required=True, help="Image tweet topic")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Generate without posting")
@click.option("--json", "as_json", is_flag=True)
def x_image(topic, language, auto_approve, dry_run, as_json):
    """Generate and post an image tweet (AI-generated 16:9 image)."""
    orch = _get_x_orchestrator()
    result = asyncio.run(
        orch.post(
            content_type="image_tweet",
            topic=topic,
            language=language,
            auto_approve=auto_approve,
            dry_run=dry_run,
        )
    )
    _out(result, as_json)


@x.command("video")
@click.option("--topic", required=True, help="Video tweet topic")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Generate without posting")
@click.option("--json", "as_json", is_flag=True)
def x_video(topic, language, auto_approve, dry_run, as_json):
    """Generate and post a video tweet (HeyGen video)."""
    orch = _get_x_orchestrator()
    result = asyncio.run(
        orch.post(
            content_type="video_tweet",
            topic=topic,
            language=language,
            auto_approve=auto_approve,
            dry_run=dry_run,
        )
    )
    _out(result, as_json)


@x.command("cross-post")
@click.option("--linkedin-text", required=True, help="LinkedIn post text to adapt for X")
@click.option("--language", default="en", type=click.Choice(["en", "pt"]), help="Language")
@click.option("--auto-approve", is_flag=True, help="Skip Telegram approval")
@click.option("--dry-run", is_flag=True, help="Generate without posting")
@click.option("--json", "as_json", is_flag=True)
def x_cross_post(linkedin_text, language, auto_approve, dry_run, as_json):
    """Adapt a LinkedIn post to an X thread and publish."""
    orch = _get_x_orchestrator()
    result = asyncio.run(
        orch.post(
            content_type="thread",
            language=language,
            auto_approve=auto_approve,
            dry_run=dry_run,
            cross_post_from_linkedin=linkedin_text,
        )
    )
    _out(result, as_json)


@x.command("analytics")
@click.option("--post-id", type=int, required=True, help="x_posts.id to fetch analytics for")
@click.option("--json", "as_json", is_flag=True)
def x_analytics_cmd(post_id, as_json):
    """Fetch and display analytics for a posted tweet."""
    from eworks.agents.publisher.x_analytics import XAnalyticsCollector
    db = _get_db()
    db.add_x_publisher_tables()
    collector = XAnalyticsCollector(db)
    # Look up tweet_id for the post
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT tweet_id FROM x_posts WHERE id=?", (post_id,)
        ).fetchone()
    if not row or not row[0]:
        click.echo(f"No tweet_id found for post_id={post_id}", err=True)
        return
    tweet_id = row[0]
    analytics = collector.collect(post_id, tweet_id)
    _out(analytics, as_json)


@x.command("list")
@click.option("--status", default=None, help="Filter by status (draft/posted/failed/etc.)")
@click.option("--limit", default=20, type=int)
@click.option("--json", "as_json", is_flag=True)
def x_list(status, limit, as_json):
    """List X posts from DB."""
    db = _get_db()
    db.add_x_publisher_tables()
    with db.get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT id, content_type, status, text_content, tweet_url, posted_at "
                "FROM x_posts WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, content_type, status, text_content, tweet_url, posted_at "
                "FROM x_posts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    posts = [
        {
            "id": r[0],
            "content_type": r[1],
            "status": r[2],
            "text": r[3][:80] if r[3] else "",
            "tweet_url": r[4],
            "posted_at": r[5],
        }
        for r in rows
    ]
    _out(posts, as_json)


@x.command("schedule")
@click.option("--topic", required=True, help="Content topic")
@click.option(
    "--type",
    "content_type",
    default="tweet",
    type=click.Choice(["tweet", "thread", "image_tweet", "video_tweet"]),
)
@click.option("--cron", default="0 9 * * 1-5", help="Cron expression (default: Mon-Fri 9 AM)")
@click.option("--json", "as_json", is_flag=True)
def x_schedule(topic, content_type, cron, as_json):
    """Show scheduling config for X posts (add to cron to activate)."""
    info = {
        "topic": topic,
        "content_type": content_type,
        "cron": cron,
        "optimal_times": "Mon-Fri at 9 AM, 10 AM, noon, or 5 PM",
        "max_per_day": 5,
        "command": (
            f"eworks x {content_type.replace('_tweet', '')} "
            f"--topic \"{topic}\" --auto-approve"
        ),
        "message": "Add the above command to a cron job using the specified cron expression.",
    }
    _out(info, as_json)


# ─── youtube (extended) ───────────────────────────────────────────────────────


@cli.group("youtube")
def youtube_group():
    """YouTube extended publisher commands."""


@youtube_group.command("shorts")
@click.option("--video", "video_path", required=True, help="Path to video file")
@click.option("--title", required=True, help="Video title")
@click.option("--description", default="", help="Video description")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--json", "as_json", is_flag=True)
def youtube_shorts(video_path: str, title: str, description: str, tags: str, as_json: bool):
    """Upload a YouTube Short (#Shorts tag auto-added)."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = YouTubePoster()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = poster.make_youtube_short(video_path, title, description, tags=tag_list)
    _out(result, as_json)


@youtube_group.command("thumbnail")
@click.option("--video-id", required=True, help="YouTube video ID")
@click.option("--topic", required=True, help="Topic/subject for AI thumbnail generation")
@click.option("--title", default="", help="Video title for thumbnail prompt")
@click.option("--json", "as_json", is_flag=True)
def youtube_thumbnail(video_id: str, topic: str, title: str, as_json: bool):
    """Generate + set AI thumbnail for a YouTube video."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    from eworks.agents.publisher.thumbnail_generator import ThumbnailGenerator
    db = _get_db()
    db.add_extended_media_tables()
    gen = ThumbnailGenerator()
    thumbnail_path = gen.generate_youtube_thumbnail(title or topic, topic)
    poster = YouTubePoster()
    success = poster.set_thumbnail(video_id, thumbnail_path)
    _out({"video_id": video_id, "thumbnail_path": thumbnail_path, "status": "set" if success else "failed"}, as_json)


@youtube_group.command("captions")
@click.option("--video-id", required=True, help="YouTube video ID")
@click.option("--script", "script_file", required=True, type=click.Path(exists=True), help="Path to script text file")
@click.option("--language", default="en", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def youtube_captions(video_id: str, script_file: str, language: str, as_json: bool):
    """Generate SRT captions from script and upload to YouTube."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    from eworks.agents.publisher.caption_generator import CaptionGenerator
    db = _get_db()
    db.add_extended_media_tables()
    script_text = Path(script_file).read_text(encoding="utf-8")
    gen = CaptionGenerator()
    srt = gen.generate_srt(script_text)
    poster = YouTubePoster()
    result = poster.upload_captions(video_id, srt, language=language)
    _out(result, as_json)


@youtube_group.command("playlist")
@click.option("--video-id", required=True, help="YouTube video ID")
@click.option("--playlist", "playlist_title", default="Eworks Labs", show_default=True, help="Playlist name")
@click.option("--json", "as_json", is_flag=True)
def youtube_playlist(video_id: str, playlist_title: str, as_json: bool):
    """Add a video to a YouTube playlist (creates if missing)."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = YouTubePoster()
    result = poster.add_to_playlist(video_id, playlist_title=playlist_title)
    _out(result, as_json)


@youtube_group.command("schedule")
@click.option("--video-id", required=True, help="YouTube video ID")
@click.option("--publish-at", required=True, help="ISO8601 datetime e.g. 2026-06-01T09:00:00Z")
@click.option("--json", "as_json", is_flag=True)
def youtube_schedule(video_id: str, publish_at: str, as_json: bool):
    """Schedule a YouTube video to go public at a specific time."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = YouTubePoster()
    success = poster.set_scheduled_publish(video_id, publish_at)
    _out({"video_id": video_id, "publish_at": publish_at, "status": "scheduled" if success else "failed"}, as_json)


@youtube_group.command("analytics")
@click.option("--video-id", required=True, help="YouTube video ID")
@click.option("--json", "as_json", is_flag=True)
def youtube_analytics(video_id: str, as_json: bool):
    """Fetch analytics for a YouTube video."""
    from eworks.agents.publisher.social_poster import YouTubePoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = YouTubePoster()
    result = poster.get_video_analytics(video_id)
    _out(result, as_json)


# ─── instagram (extended) ─────────────────────────────────────────────────────


@cli.group("instagram")
def instagram_group():
    """Instagram extended publisher commands."""


@instagram_group.command("story")
@click.option("--image", "image_path", required=True, help="Path to image file")
@click.option("--mention", default=None, help="Optional @username to mention")
@click.option("--json", "as_json", is_flag=True)
def instagram_story(image_path: str, mention: str, as_json: bool):
    """Post an image Story to Instagram (24h ephemeral)."""
    from eworks.agents.publisher.social_poster import InstagramPoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = InstagramPoster()
    result = asyncio.run(poster.post_story_image(image_path, mention=mention))
    _out(result, as_json)


@instagram_group.command("story-video")
@click.option("--video", "video_path", required=True, help="Path to video file")
@click.option("--json", "as_json", is_flag=True)
def instagram_story_video(video_path: str, as_json: bool):
    """Post a video Story to Instagram."""
    from eworks.agents.publisher.social_poster import InstagramPoster
    db = _get_db()
    db.add_extended_media_tables()
    poster = InstagramPoster()
    result = asyncio.run(poster.post_story_video(video_path))
    _out(result, as_json)


@instagram_group.command("hashtags")
@click.option("--topic", required=True, help="Topic for hashtag research")
@click.option("--language", default="en", show_default=True, help="en or pt")
@click.option("--json", "as_json", is_flag=True)
def instagram_hashtags(topic: str, language: str, as_json: bool):
    """Generate optimized Instagram hashtags for a topic."""
    from eworks.agents.publisher.hashtag_researcher import HashtagResearcher
    researcher = HashtagResearcher()
    hashtags = asyncio.run(researcher.get_optimal_hashtags(topic, language=language))
    _out({"topic": topic, "hashtags": hashtags, "count": len(hashtags)}, as_json)


@instagram_group.command("auto-reply")
@click.option("--post-id", required=True, help="Instagram media/post ID")
@click.option("--topic", required=True, help="Post topic (for reply context)")
@click.option("--language", default="en", show_default=True)
@click.option("--max-replies", default=5, type=int, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def instagram_auto_reply(post_id: str, topic: str, language: str, max_replies: int, as_json: bool):
    """Auto-reply to recent comments on an Instagram post."""
    from eworks.agents.publisher.ig_engagement import IGEngagementManager
    db = _get_db()
    db.add_extended_media_tables()
    manager = IGEngagementManager()
    result = asyncio.run(manager.auto_reply_to_recent(post_id, topic, language=language, max_replies=max_replies))
    _out(result, as_json)


@instagram_group.command("reel-with-cover")
@click.option("--video", "video_path", required=True, help="Path to video file (will be uploaded to CDN)")
@click.option("--caption", required=True, help="Reel caption")
@click.option("--cover-topic", default=None, help="Topic for AI cover generation")
@click.option("--json", "as_json", is_flag=True)
def instagram_reel_with_cover(video_path: str, caption: str, cover_topic: str, as_json: bool):
    """Post a Reel with an AI-generated cover image."""
    from eworks.agents.publisher.social_poster import InstagramPoster
    from eworks.agents.publisher.thumbnail_generator import ThumbnailGenerator
    db = _get_db()
    db.add_extended_media_tables()
    poster = InstagramPoster()

    async def _run():
        video_url = await poster.upload_file_to_cdn(video_path)
        cover_url = None
        if cover_topic:
            gen = ThumbnailGenerator()
            cover_path = gen.generate_reel_cover(cover_topic)
            cover_url = await poster.upload_file_to_cdn(cover_path)
        return await poster.post_reel_with_cover(video_url, caption, cover_url=cover_url)

    result = asyncio.run(_run())
    _out(result, as_json)


# ─── connector ────────────────────────────────────────────────────────────────


@cli.group()
def connector():
    """Connector agent — monitor and reply across all social platforms."""


@connector.command('run')
@click.option('--platform', default='all',
              type=click.Choice(['all', 'instagram', 'linkedin', 'x', 'youtube']),
              show_default=True)
@click.option('--since', default=60, show_default=True, help='Minutes to look back for new interactions')
@click.option('--json', 'as_json', is_flag=True)
def connector_run(platform: str, since: int, as_json: bool):
    """Scan platforms and process new interactions."""
    from eworks.core.config import get_config
    db = _get_db()
    db.add_connector_tables()
    cfg = get_config()
    from eworks.agents.connector.orchestrator import ConnectorOrchestrator
    agent = ConnectorOrchestrator(db, cfg)
    if platform == 'all':
        result = asyncio.run(agent.run_all(since_minutes=since))
    else:
        result = asyncio.run(agent.run_platform(platform, since_minutes=since))
    _out(result, as_json)


@connector.command('inbox')
@click.option('--platform', default=None,
              type=click.Choice(['instagram', 'linkedin', 'x', 'youtube']))
@click.option('--limit', default=20, show_default=True)
@click.option('--json', 'as_json', is_flag=True)
def connector_inbox(platform: str, limit: int, as_json: bool):
    """Show all pending interactions waiting for reply."""
    db = _get_db()
    db.add_connector_tables()
    from eworks.agents.connector.conversation_tracker import ConversationTracker
    tracker = ConversationTracker(db)
    rows = tracker.get_pending(platform=platform, limit=limit)
    if as_json:
        _out(rows, as_json)
    else:
        if not rows:
            click.echo('No pending interactions.')
            return
        click.echo(f'\n{"=" * 70}')
        click.echo(f'  PENDING INTERACTIONS ({len(rows)})')
        click.echo(f'{"=" * 70}')
        for r in rows:
            lead_flag = ' 🔥 LEAD' if r.get('is_lead') else ''
            click.echo(
                f"\n[{r['id']}] {r['platform'].upper()}{lead_flag} | @{r.get('author_username', '?')} | {r.get('sentiment', '?')}"
            )
            click.echo(f"  Content: {r['content'][:120]}")
            click.echo(f"  Detected: {r.get('detected_at', '?')}")
        click.echo(f'{"=" * 70}\n')


@connector.command('reply')
@click.argument('interaction_id', type=int)
@click.option('--text', required=True, help='Reply text to post')
@click.option('--json', 'as_json', is_flag=True)
def connector_reply(interaction_id: int, text: str, as_json: bool):
    """Manually reply to a specific interaction."""
    db = _get_db()
    db.add_connector_tables()
    from eworks.agents.connector.conversation_tracker import ConversationTracker
    from eworks.core.config import get_config
    from eworks.agents.connector.orchestrator import ConnectorOrchestrator
    tracker = ConversationTracker(db)
    # Fetch interaction
    with db.get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM social_interactions WHERE id=?', (interaction_id,)
        ).fetchone()
    if not row:
        click.echo(f'Interaction {interaction_id} not found.', err=True)
        return
    cols = [
        'id', 'platform', 'interaction_type', 'external_id', 'parent_id',
        'author_username', 'author_id', 'author_name', 'content', 'url',
    ]
    interaction = dict(zip(cols, row[:10]))
    cfg = get_config()
    agent = ConnectorOrchestrator(db, cfg)

    async def _do_reply():
        return await agent._post_reply(interaction['platform'], interaction, text)

    result = asyncio.run(_do_reply())
    if result.get('status') == 'replied':
        tracker.mark_replied(interaction_id, text, result.get('reply_id', ''))
        click.echo(f'✓ Replied to interaction {interaction_id}')
    else:
        click.echo(f'✗ Reply failed: {result}', err=True)
    _out(result, as_json)


@connector.command('ignore')
@click.argument('interaction_id', type=int)
def connector_ignore(interaction_id: int):
    """Mark an interaction as ignored."""
    db = _get_db()
    db.add_connector_tables()
    from eworks.agents.connector.conversation_tracker import ConversationTracker
    tracker = ConversationTracker(db)
    tracker.mark_ignored(interaction_id)
    click.echo(f'✓ Interaction {interaction_id} marked as ignored.')


@connector.command('status')
@click.option('--json', 'as_json', is_flag=True)
def connector_status(as_json: bool):
    """Show connector stats: handled, escalated, leads detected."""
    db = _get_db()
    db.add_connector_tables()
    from eworks.agents.connector.conversation_tracker import ConversationTracker
    tracker = ConversationTracker(db)
    stats = tracker.get_stats()
    # Last run
    with db.get_connection() as conn:
        last_run = conn.execute(
            'SELECT * FROM connector_runs ORDER BY started_at DESC LIMIT 1'
        ).fetchone()
    if last_run:
        run_cols = [
            'id', 'run_type', 'started_at', 'completed_at',
            'interactions_found', 'replies_sent', 'escalations', 'leads_detected', 'errors',
        ]
        stats['last_run'] = dict(zip(run_cols, last_run))
    _out(stats, as_json)
    if not as_json:
        click.echo(f"\n📊 Connector Status")
        click.echo(f"  Total interactions: {stats['total']}")
        click.echo(f"  Pending:   {stats['pending']}")
        click.echo(f"  Replied:   {stats['replied']}")
        click.echo(f"  Escalated: {stats['escalated']}")
        click.echo(f"  🔥 Leads:  {stats['leads']}")


@connector.command('daemon')
@click.option('--interval', default=15, show_default=True, help='Polling interval in minutes')
@click.option('--platform', default='all',
              type=click.Choice(['all', 'instagram', 'linkedin', 'x', 'youtube']),
              show_default=True)
def connector_daemon(interval: int, platform: str):
    """Run connector as a daemon, polling on interval."""
    import time
    from eworks.core.config import get_config
    db = _get_db()
    db.add_connector_tables()
    cfg = get_config()
    from eworks.agents.connector.orchestrator import ConnectorOrchestrator
    agent = ConnectorOrchestrator(db, cfg)
    click.echo(f'🤖 Connector daemon starting — polling every {interval} min (platform={platform})')
    while True:
        try:
            click.echo(f'[{datetime.now().strftime("%H:%M:%S")}] Scanning {platform}...')
            if platform == 'all':
                result = asyncio.run(agent.run_all(since_minutes=interval))
            else:
                result = asyncio.run(agent.run_platform(platform, since_minutes=interval))
            click.echo(
                f'  → found={result.get("found", 0)} replied={result.get("replied", 0)} '
                f'escalated={result.get("escalated", 0)} leads={result.get("leads", 0)}'
            )
        except KeyboardInterrupt:
            click.echo('\n✓ Connector daemon stopped.')
            break
        except Exception as e:
            logger.error('Daemon iteration error: %s', e)
            click.echo(f'  ✗ Error: {e}', err=True)
        time.sleep(interval * 60)


if __name__ == "__main__":
    cli()
