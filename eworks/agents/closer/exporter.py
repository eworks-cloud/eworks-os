"""Proposal exporter — Markdown and PDF generation."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROPOSALS_DIR = Path("data/proposals")


def _slugify(text: str, max_len: int = 40) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len]


class ProposalExporter:
    """Exports proposals to Markdown and PDF formats."""

    def __init__(self, db, base_dir: str | Path = PROPOSALS_DIR):
        self.db = db
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_proposal(self, proposal_id: int) -> dict[str, Any]:
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if not row:
            raise ValueError(f"Proposal {proposal_id} not found")
        return dict(row)

    def export_markdown(self, proposal_id: int) -> str:
        """Export proposal as Markdown file. Returns file path."""
        proposal = self._get_proposal(proposal_id)
        title = proposal.get("title", f"Proposal {proposal_id}")
        slug = _slugify(title)
        filename = f"{proposal_id}-{slug}.md"
        path = self.base_dir / filename

        content = proposal.get("markdown_content", "")
        if not content:
            content = f"# {title}\n\n*No content generated yet.*\n"

        path.write_text(content, encoding="utf-8")
        logger.info("Exported markdown: %s", path)
        return str(path)

    def export_pdf(self, proposal_id: int) -> str:
        """
        Export proposal as PDF (or fallback .txt if weasyprint unavailable).
        Updates proposals.pdf_path in DB. Returns file path.
        """
        proposal = self._get_proposal(proposal_id)
        title = proposal.get("title", f"Proposal {proposal_id}")
        slug = _slugify(title)
        content = proposal.get("markdown_content", "")

        # Try weasyprint + markdown2
        pdf_path = self._try_pdf_export(proposal_id, slug, title, content)

        # Update DB
        conn = self.db.get_connection()
        conn.execute("UPDATE proposals SET pdf_path=? WHERE id=?", (pdf_path, proposal_id))
        conn.commit()
        logger.info("Exported PDF/document: %s", pdf_path)
        return pdf_path

    def _try_pdf_export(self, proposal_id: int, slug: str, title: str, content: str) -> str:
        """Attempt PDF via weasyprint, fallback to styled .txt."""
        try:
            import markdown2  # type: ignore
            from weasyprint import HTML  # type: ignore

            html_body = markdown2.markdown(content, extras=["tables", "fenced-code-blocks"])
            html_full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; color: #222; line-height: 1.6; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #4a90d9; padding-bottom: 8px; }}
  h2 {{ color: #16213e; margin-top: 2em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #4a90d9; color: white; }}
  code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
            pdf_file = self.base_dir / f"{proposal_id}-{slug}.pdf"
            HTML(string=html_full).write_pdf(str(pdf_file))
            return str(pdf_file)

        except ImportError as exc:
            logger.warning("PDF library not available (%s), falling back to .txt", exc)
            return self._export_txt(proposal_id, slug, title, content)
        except Exception as exc:
            logger.error("PDF generation failed (%s), falling back to .txt", exc)
            return self._export_txt(proposal_id, slug, title, content)

    def _export_txt(self, proposal_id: int, slug: str, title: str, content: str) -> str:
        """Fallback: export as formatted plain text file."""
        txt_file = self.base_dir / f"{proposal_id}-{slug}.txt"
        # Add a nice header
        header = f"{'=' * 70}\n{title.upper()}\n{'=' * 70}\n\n"
        # Convert basic markdown headers to plain text
        plain = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
        txt_file.write_text(header + plain, encoding="utf-8")
        return str(txt_file)
