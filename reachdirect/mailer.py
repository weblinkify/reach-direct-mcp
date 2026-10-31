"""Brevo (ex-Sendinblue) v3 transactional email over HTTPS."""

from __future__ import annotations

import html
import re
from typing import Any

import httpx

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}$")


class EmailError(ValueError):
    pass


def valid_email(addr: str) -> bool:
    return bool(EMAIL_RE.match(addr.strip()))


def text_to_html(text: str) -> str:
    """Plain text to simple HTML paragraphs (escaped, line breaks kept)."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def build_payload(
    to_email: str,
    to_name: str | None,
    sender_email: str,
    sender_name: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> dict[str, Any]:
    for label, addr in (("recipient", to_email), ("sender", sender_email)):
        if not valid_email(addr):
            raise EmailError(f"Invalid {label} email address: {addr!r}")
    if reply_to and not valid_email(reply_to):
        raise EmailError(f"Invalid reply-to address: {reply_to!r}")
    if not subject.strip():
        raise EmailError("Subject is empty.")
    if not body.strip():
        raise EmailError("Message body is empty.")
    payload: dict[str, Any] = {
        "sender": {"name": sender_name.strip() or sender_email, "email": sender_email.strip()},
        "to": [
            {
                "email": to_email.strip(),
                **({"name": to_name.strip()} if to_name and to_name.strip() else {}),
            }
        ],
        "subject": subject.strip(),
        "textContent": body,
        "htmlContent": text_to_html(body),
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to.strip()}
    return payload


async def send(
    payload: dict[str, Any], api_key: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Sends through Brevo. Returns {"ok": True, "message_id": ...} or {"ok": False, "error": ...}."""
    if not api_key:
        return {
            "ok": False,
            "error": "BREVO_API_KEY is not set. Add it to the MCP server's env block.",
        }
    headers = {"api-key": api_key, "accept": "application/json", "content-type": "application/json"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=20.0)
    try:
        resp = await client.post(BREVO_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "error": f"Network error talking to Brevo: {exc or exc.__class__.__name__}",
        }
    finally:
        if own:
            await client.aclose()
    if resp.status_code in (200, 201, 202):
        try:
            message_id = resp.json().get("messageId")
        except ValueError:
            message_id = None
        return {"ok": True, "message_id": message_id}
    try:
        detail = resp.json().get("message") or resp.text
    except ValueError:
        detail = resp.text
    hint = {
        401: "The API key was rejected. Check BREVO_API_KEY.",
        400: "Brevo rejected the request. A common cause is a sender address that is not verified in Brevo (Senders & IP).",
        402: "Your Brevo plan has no email credits left today.",
        429: "Brevo rate limit reached. Wait and retry.",
    }.get(resp.status_code, "")
    return {"ok": False, "status": resp.status_code, "error": f"{detail} {hint}".strip()}
