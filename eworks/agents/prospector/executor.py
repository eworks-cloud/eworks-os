"""Outreach executor — sends LinkedIn connection requests with rate limiting.

Hard limits:
- Max 20 connection requests per day
- Active only during configured time windows
- Random 30–90 second delays between sends
- Immediate stop on LinkedIn restriction warnings
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, time as dt_time
from typing import Any

from eworks.agents.prospector.auth import LinkedInAuth, random_delay
from eworks.core.phoenix_instrumentation import trace_tool_call, trace_workflow_step

logger = logging.getLogger(__name__)

MAX_DAILY_REQUESTS = 20
DEFAULT_TIME_WINDOWS = [
    (dt_time(9, 0), dt_time(11, 30)),
    (dt_time(14, 0), dt_time(16, 30)),
]

RESTRICTION_SIGNALS = [
    "you've reached the weekly invitation limit",
    "we restrict certain activities on linkedin",
    "your account has been restricted",
    "action blocked",
    "please verify",
]


def _is_within_window(windows=None) -> bool:
    """Return True if the current time falls within any allowed send window."""
    windows = windows or DEFAULT_TIME_WINDOWS
    now = datetime.now().time()
    for start, end in windows:
        if start <= now <= end:
            return True
    return False


async def _action_delay() -> None:
    """Wait 30–90 seconds between sends to mimic human behaviour."""
    delay = random.uniform(30, 90)
    logger.debug("Rate-limit delay: %.1fs", delay)
    await asyncio.sleep(delay)


class OutreachExecutor:
    """Executes LinkedIn connection request outreach campaigns."""

    def __init__(
        self,
        daily_limit: int = MAX_DAILY_REQUESTS,
        time_windows=None,
    ):
        self.daily_limit = daily_limit
        self.time_windows = time_windows or DEFAULT_TIME_WINDOWS

    @trace_tool_call("linkedin_send_connection_request")
    async def send_connection_request(
        self,
        auth: LinkedInAuth,
        linkedin_url: str,
        message: str,
    ) -> bool:
        """Visit a profile and send a connection request with a personalised note.

        Returns True on success, False on any failure.
        """
        if auth.page is None:
            logger.error("Browser not started")
            return False

        page = auth.page

        try:
            logger.info("Visiting profile: %s", linkedin_url)
            await page.goto(linkedin_url, wait_until="domcontentloaded")
            await random_delay(2.0, 4.0)

            # Check for restriction warnings
            content = await page.content()
            content_lower = content.lower()
            for signal in RESTRICTION_SIGNALS:
                if signal in content_lower:
                    logger.warning("RESTRICTION DETECTED: %s", signal)
                    raise RuntimeError(f"LinkedIn restriction detected: {signal}")

            # Check if already connected
            connected_el = await page.query_selector(
                "button[aria-label='Message'], .pvs-profile-actions__action[aria-label*='Message']"
            )
            if connected_el:
                logger.info("Already connected with %s — skipping", linkedin_url)
                return False

            # Check if connection request is pending
            pending_el = await page.query_selector(
                "button[aria-label='Pending'], [aria-label*='Pending']"
            )
            if pending_el:
                logger.info("Connection request already pending for %s", linkedin_url)
                return False

            # Find the Connect button
            connect_button = await page.query_selector(
                "button[aria-label='Connect'], "
                ".pvs-profile-actions__action[aria-label='Connect'], "
                "button:has-text('Connect')"
            )
            if not connect_button:
                # Try the "More" dropdown
                more_button = await page.query_selector(
                    "button[aria-label='More actions'], button:has-text('More')"
                )
                if more_button:
                    await more_button.click()
                    await random_delay(1.0, 2.0)
                    connect_button = await page.query_selector(
                        "[aria-label='Connect']"
                    )

            if not connect_button:
                logger.warning("No Connect button found for %s", linkedin_url)
                return False

            await connect_button.click()
            await random_delay(1.5, 3.0)

            # Look for "Add a note" option
            add_note_btn = await page.query_selector(
                "button[aria-label='Add a note'], button:has-text('Add a note')"
            )
            if add_note_btn:
                await add_note_btn.click()
                await random_delay(1.0, 2.0)

                # Type the message character by character (human-like)
                textarea = await page.query_selector(
                    "textarea#custom-message, textarea[name='message']"
                )
                if textarea:
                    await textarea.click()
                    for char in message:
                        await textarea.type(char)
                        await asyncio.sleep(random.uniform(0.02, 0.08))
                    await random_delay(1.0, 2.0)

            # Send the request
            send_button = await page.query_selector(
                "button[aria-label='Send now'], button:has-text('Send')"
            )
            if not send_button:
                send_button = await page.query_selector(
                    "button[aria-label='Send without a note'], button:has-text('Send without a note')"
                )

            if send_button:
                await send_button.click()
                await random_delay(2.0, 4.0)
                logger.info("Connection request sent to %s", linkedin_url)
                return True
            else:
                logger.warning("Send button not found for %s", linkedin_url)
                return False

        except RuntimeError:
            raise  # Re-raise restriction errors
        except Exception as exc:
            logger.error("Error sending connection request to %s: %s", linkedin_url, exc)
            return False

    @trace_workflow_step("run_campaign")
    async def run_campaign(
        self,
        auth: LinkedInAuth,
        db,
        campaign_id: int,
        daily_limit: int | None = None,
    ) -> dict[str, int]:
        """Run outreach for a campaign. Returns {sent, failed, skipped}."""
        limit = daily_limit or self.daily_limit
        summary = {"sent": 0, "failed": 0, "skipped": 0}

        if not _is_within_window(self.time_windows):
            logger.info("Outside allowed send windows — skipping campaign run")
            summary["skipped"] = -1  # sentinel: wrong time
            return summary

        # Get campaign info
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            logger.error("Campaign %d not found", campaign_id)
            return summary

        # Check today's sent count
        conn = db.get_connection()
        today_str = datetime.utcnow().date().isoformat()
        today_sent = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM messages
            WHERE campaign_id=? AND message_type='connection_request'
            AND DATE(sent_at)=?
            """,
            (campaign_id, today_str),
        ).fetchone()
        sent_today = today_sent["cnt"] if today_sent else 0

        if sent_today >= limit:
            logger.info(
                "Daily limit reached (%d/%d) for campaign %d",
                sent_today, limit, campaign_id,
            )
            summary["skipped"] = -2  # sentinel: daily limit
            return summary

        remaining = limit - sent_today

        # Fetch queued prospects
        threshold = campaign.get("icp_score_threshold") or 0.0
        rows = conn.execute(
            """
            SELECT p.*, m.body as message_body
            FROM prospects p
            LEFT JOIN messages m ON m.prospect_id = p.id
                AND m.status = 'draft'
                AND m.campaign_id = ?
            WHERE p.campaign_id = ?
              AND p.status = 'queued'
              AND p.icp_score >= ?
            ORDER BY p.icp_score DESC
            LIMIT ?
            """,
            (campaign_id, campaign_id, threshold, remaining),
        ).fetchall()

        prospects = [dict(r) for r in rows]
        logger.info(
            "Campaign %d: %d prospects queued, daily remaining=%d",
            campaign_id, len(prospects), remaining,
        )

        for prospect in prospects:
            if summary["sent"] >= remaining:
                break

            linkedin_url = prospect.get("linkedin_url", "")
            message = prospect.get("message_body", "")

            if not message:
                logger.warning("No draft message for prospect %s — skipping", linkedin_url)
                summary["skipped"] += 1
                continue

            try:
                success = await self.send_connection_request(auth, linkedin_url, message)
                now = datetime.utcnow().isoformat()

                if success:
                    # Update prospect status
                    db.get_connection().execute(
                        "UPDATE prospects SET status='contacted', contacted_at=? WHERE id=?",
                        (now, prospect["id"]),
                    )
                    # Update message status
                    db.get_connection().execute(
                        "UPDATE messages SET status='sent', sent_at=? WHERE prospect_id=? AND status='draft'",
                        (now, prospect["id"]),
                    )
                    db.get_connection().commit()
                    summary["sent"] += 1
                    logger.info("✓ Sent to %s", prospect.get("full_name", linkedin_url))
                else:
                    summary["failed"] += 1

                # Rate limiting delay
                if summary["sent"] < remaining:
                    await _action_delay()

            except RuntimeError as exc:
                # Restriction detected — stop immediately
                logger.error("STOPPING campaign: %s", exc)
                summary["failed"] += 1
                break
            except Exception as exc:
                logger.error("Unexpected error for %s: %s", linkedin_url, exc)
                summary["failed"] += 1

        logger.info(
            "Campaign %d run complete: sent=%d failed=%d skipped=%d",
            campaign_id, summary["sent"], summary["failed"], summary["skipped"],
        )
        return summary
