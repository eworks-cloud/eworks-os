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


if __name__ == "__main__":
    cli()
