"""
Email digest notifications for new high-score matches.
Uses Python's built-in smtplib — no extra dependency.
Configure via SMTP_* env vars. Silently skips if not configured.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def send_match_digest(
    to_email: str,
    matches: list[dict],  # [{title, company, location, score, url, explanation}, ...]
    user_name: Optional[str] = None,
) -> bool:
    """
    Send a digest email listing new high-score job matches.
    Returns True on success, False on failure or if SMTP is not configured.
    """
    if not _smtp_configured():
        logger.debug("[notifications] SMTP not configured — skipping digest")
        return False

    if not matches:
        return False

    greeting = f"Hi {user_name}," if user_name else "Hi,"
    rows_html = "\n".join(
        f"""
        <tr>
          <td style="padding:8px 0; border-bottom:1px solid #eee;">
            <strong>{m['title']}</strong> at {m['company']}<br>
            <span style="color:#6b7280;font-size:13px;">{m.get('location') or ''}</span>
            {f'<br><em style="color:#3b82f6;font-size:13px;">{m["explanation"]}</em>' if m.get('explanation') else ''}
          </td>
          <td style="padding:8px 0;border-bottom:1px solid #eee;text-align:right;vertical-align:top;white-space:nowrap;">
            <span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600;">
              {round(m['score'] * 100)}%
            </span><br>
            {'<a href="' + m["url"] + '" style="font-size:12px;color:#3b82f6;">Apply →</a>' if m.get('url') else ''}
          </td>
        </tr>"""
        for m in matches
    )

    html = f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#111;">
      <h2 style="color:#1d4ed8;">Job Matcher — {len(matches)} new match{'es' if len(matches) != 1 else ''}</h2>
      <p>{greeting}</p>
      <p>Here are your top new job matches since your last digest:</p>
      <table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>
      <p style="margin-top:24px;">
        <a href="{settings.app_base_url}/jobs"
           style="background:#2563eb;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">
          View all matches →
        </a>
      </p>
      <p style="color:#9ca3af;font-size:12px;margin-top:32px;">
        You're receiving this because you enabled match notifications.
        <a href="{settings.app_base_url}/settings" style="color:#9ca3af;">Manage preferences</a>
      </p>
    </html></body>
    """

    text = f"{greeting}\n\nYour top {len(matches)} new job matches:\n\n" + "\n".join(
        f"• {m['title']} at {m['company']} — {round(m['score'] * 100)}%"
        + (f"\n  {m['explanation']}" if m.get('explanation') else "")
        + (f"\n  Apply: {m['url']}" if m.get('url') else "")
        for m in matches
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Job Matcher: {len(matches)} new match{'es' if len(matches) != 1 else ''} for you"
    msg["From"] = settings.smtp_from_email or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        logger.info("[notifications] Digest sent to %s (%d matches)", to_email, len(matches))
        return True
    except Exception as exc:
        logger.error("[notifications] Failed to send digest to %s: %s", to_email, exc)
        return False
