# SYNAPSE Email Sender
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md §3.5, 05_INTEGRATION.md §5.2
#
# Sends emails from Agent A to the supervisor with documents
# as attachments for review/approval.

import logging
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("synapse.email")

# SMTP configuration (env vars)
SMTP_HOST = os.getenv("SYNAPSE_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SYNAPSE_SMTP_PORT", "587"))


class SynapseEmailSender:
    """Sends emails from Agent A to the supervisor via SMTP.

    Ref: 05_INTEGRATION.md §5.2
    """

    def __init__(self):
        self._from_addr = os.getenv("SYNAPSE_SMTP_FROM", "")
        self._password = os.getenv("SYNAPSE_SMTP_PASSWORD", "")
        self._to_addr = os.getenv("SYNAPSE_SUPERVISOR_EMAIL", "")
        self._sender_name = os.getenv("SYNAPSE_SENDER_NAME", "SYNAPSE")

    @property
    def is_configured(self) -> bool:
        return bool(self._from_addr and self._password and self._to_addr)

    def send_docs_for_review(
        self,
        session_id: str,
        session_dir: str,
        summary: str,
        file_paths: Optional[List[str]] = None,
    ) -> dict:
        """Sends conceptualization documents for supervisor review.

        Triggered at end of Phase 1 (CONCEPTUALIZING → AWAITING_APPROVAL).
        Ref: 04_SUPERVISION.md §2.2
        """
        subject = f"[SYNAPSE] {session_id} — Documents for review"

        body = f"""Hello,

The conceptualization documents are ready for your review:

{summary}

Session directory:
  {session_dir}

Actions:
  /synapse approve — Approve and start implementation
  /synapse reject [reason] — Reject with comment

— {self._sender_name}"""

        # Auto-discover files if not specified
        if not file_paths:
            file_paths = self._discover_docs(session_dir)

        return self._send(subject, body, file_paths)

    def send_session_report(
        self,
        session_id: str,
        session_dir: str,
        report: str,
        deliverables: Optional[List[str]] = None,
    ) -> dict:
        """Sends the end-of-session report with deliverables.

        Triggered at end of session (COMPLETED).
        Ref: 02_PROTOCOLE.md §3.5, 04_SUPERVISION.md §3.5
        """
        subject = f"[SYNAPSE] {session_id} — Session completed"

        body = f"""Hello,

Here are the deliverables for session {session_id}:

{report}

Session directory:
  {session_dir}

— {self._sender_name}"""

        # Auto-discover files if not specified
        if not deliverables:
            deliverables = self._discover_deliverables(session_dir)

        return self._send(subject, body, deliverables)

    def send_custom(
        self,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
    ) -> dict:
        """Generic send for non-standard cases."""
        return self._send(subject, body, attachments or [])

    def _send(self, subject: str, body: str, attachments: List[str]) -> dict:
        """Actual send via SMTP."""
        if not self.is_configured:
            logger.warning("Email not configured (SYNAPSE_SMTP_FROM / SYNAPSE_SMTP_PASSWORD / SYNAPSE_SUPERVISOR_EMAIL)")
            return {"success": False, "error": "Email not configured"}

        msg = MIMEMultipart()
        msg["From"] = f"{self._sender_name} <{self._from_addr}>"
        msg["To"] = self._to_addr
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attachments
        attached_files = []
        for filepath in attachments:
            p = Path(filepath)
            if not p.exists():
                logger.warning("Attachment file not found: %s", filepath)
                continue
            if p.stat().st_size > 10 * 1024 * 1024:  # 10 MB max
                logger.warning("File too large (>10MB): %s", filepath)
                continue

            try:
                part = MIMEBase("application", "octet-stream")
                with open(p, "rb") as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={p.name}",
                )
                msg.attach(part)
                attached_files.append(p.name)
            except Exception as e:
                logger.error("Error adding attachment %s: %s", filepath, e)

        # SMTP send
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(self._from_addr, self._password)
                server.send_message(msg)

            logger.info("Email sent: %s (%s attachments)", subject, len(attached_files))
            return {
                "success": True,
                "to": self._to_addr,
                "subject": subject,
                "attachments": attached_files,
            }

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed — check credentials")
            return {"success": False, "error": "SMTP authentication failed"}
        except Exception as e:
            logger.error("Email send error: %s", e)
            return {"success": False, "error": str(e)}

    def _discover_docs(self, session_dir: str) -> List[str]:
        """Auto-discovers all session documents for review.

        Includes protocol files (objective, journal) AND all
        generated documents (analyses, plans, reports, projections).
        """
        files = []
        seen = set()
        d = Path(session_dir)
        if not d.exists():
            return files

        # 1. Protocol files (in order)
        for name in ["00_OBJECTIVE.md", "01_PLAN.md", "02_JOURNAL.md"]:
            f = d / name
            if f.exists():
                files.append(str(f))
                seen.add(f.name)

        # 2. Generated documents in docs/
        docs_dir = d / "docs"
        if docs_dir.exists():
            for f in sorted(docs_dir.glob("*.md")):
                if f.name not in seen:
                    files.append(str(f))
                    seen.add(f.name)

        # 3. Any other .md at session root
        for f in sorted(d.glob("*.md")):
            if f.name not in seen:
                files.append(str(f))
                seen.add(f.name)

        return files

    def _discover_deliverables(self, session_dir: str) -> List[str]:
        """Auto-discovers deliverables (results + code) in session directory."""
        files = []
        d = Path(session_dir)
        if not d.exists():
            return files

        # Results report
        for name in ["03_RESULTS.md", "RESULTS.md"]:
            f = d / name
            if f.exists():
                files.append(str(f))

        # Generated code files
        code_dir = d / "code"
        if code_dir.exists():
            for f in sorted(code_dir.rglob("*.py")):
                files.append(str(f))

        # Tests
        tests_dir = d / "tests"
        if tests_dir.exists():
            for f in sorted(tests_dir.rglob("*.py")):
                files.append(str(f))

        # Documents docs/
        docs_dir = d / "docs"
        if docs_dir.exists():
            for f in sorted(docs_dir.glob("*.md")):
                files.append(str(f))

        return files


# Singleton
_email_sender: Optional[SynapseEmailSender] = None


def get_email_sender() -> SynapseEmailSender:
    """Returns the singleton email sender instance."""
    global _email_sender
    if _email_sender is None:
        _email_sender = SynapseEmailSender()
    return _email_sender
