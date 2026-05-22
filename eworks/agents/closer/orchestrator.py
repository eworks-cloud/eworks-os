"""Closer orchestrator — end-to-end proposal generation pipeline."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.agents.closer.discovery_processor import DiscoveryProcessor
from eworks.agents.closer.proposal_generator import ProposalGenerator
from eworks.agents.closer.exporter import ProposalExporter
from eworks.agents.closer.delivery import ProposalDelivery
from eworks.core.phoenix_instrumentation import trace_agent_execution, trace_workflow_step

logger = logging.getLogger(__name__)


class CloserOrchestrator(BaseAgent):
    """
    Orchestrates the full proposal generation pipeline:
    notes → discovery → proposal → export → deliver → track
    """

    async def run(self, campaign_id: int) -> dict:
        """BaseAgent interface — not used directly."""
        return {"status": "ok"}

    @trace_workflow_step("find_or_create_client")
    def _find_or_create_client(self, name: str, company: str) -> int:
        """Find existing client by name+company or create a new one."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT id FROM clients WHERE name=? AND (company=? OR company IS NULL)",
            (name, company),
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            """
            INSERT INTO clients (name, company, status, created_at)
            VALUES (?, ?, 'discovery', ?)
            """,
            (name, company or "", datetime.utcnow().isoformat()),
        )
        conn.commit()
        client_id = cur.lastrowid
        logger.info("Created client %d: %s @ %s", client_id, name, company)
        return client_id

    @trace_agent_execution("closer")
    async def run_from_notes(
        self,
        client_name: str,
        company: str,
        notes: str,
        deliver: bool = True,
    ) -> dict[str, Any]:
        """
        Full pipeline: notes → client → discovery call → extract → proposal → export → deliver.
        Returns summary dict.
        """
        logger.info("Starting closer pipeline for %s @ %s", client_name, company)

        # Step 1: Find or create client
        client_id = self._find_or_create_client(client_name, company)

        # Step 2: Create discovery call
        processor = DiscoveryProcessor(db=self.db, config=self.config)
        with trace_workflow_step("create_discovery_call"):
            call_id = await processor.create_call(client_id, notes)
        logger.info("Created discovery call %d", call_id)

        # Step 3: Process notes — extract requirements
        with trace_workflow_step("process_discovery_notes"):
            extraction = await processor.process_notes(call_id)
        logger.info("Extracted %d pain points, %d requirements",
                    len(extraction.get("pain_points", [])),
                    len(extraction.get("technical_requirements", [])))

        # Step 4: Generate proposal
        generator = ProposalGenerator(db=self.db, config=self.config)
        with trace_workflow_step("generate_proposal"):
            proposal_id = await generator.generate(call_id)
        logger.info("Generated proposal %d", proposal_id)

        # Step 5: Export Markdown + PDF
        exporter = ProposalExporter(db=self.db)
        with trace_workflow_step("export_proposal"):
            md_path = exporter.export_markdown(proposal_id)
            pdf_path = exporter.export_pdf(proposal_id)
        logger.info("Exported: md=%s pdf=%s", md_path, pdf_path)

        # Step 6: Deliver via Telegram
        delivered = False
        if deliver:
            delivery = ProposalDelivery(db=self.db, config=self.config)
            with trace_workflow_step("deliver_proposal"):
                delivered = await delivery.deliver_via_telegram(proposal_id)
            logger.info("Delivered: %s", delivered)

        # Step 7: Fetch final proposal for summary
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        proposal = dict(row) if row else {}

        return {
            "proposal_id": proposal_id,
            "client_id": client_id,
            "client_name": client_name,
            "company": company,
            "discovery_call_id": call_id,
            "total_price": proposal.get("total_price", 0),
            "timeline_weeks": proposal.get("timeline_weeks", 0),
            "md_path": md_path,
            "pdf_path": pdf_path,
            "delivered": delivered,
            "status": proposal.get("status", "draft"),
            "extraction": extraction,
        }
