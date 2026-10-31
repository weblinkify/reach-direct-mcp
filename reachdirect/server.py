"""ReachDirect MCP server. Run with ``python -m reachdirect`` or ``reachdirect``."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP

from . import mailer, whatsapp
from .templates import first_name, render
from .tracker import DoNotContact, OutreachLog

mcp = FastMCP(
    "ReachDirect",
    instructions=(
        "Personal outreach. Always show the user the final message (preview_message) and get their OK before "
        "send_email or send_whatsapp. Log every contact with save_outreach_contact. If someone asks not to be "
        "contacted, call add_do_not_contact; sends to those people are refused."
    ),
)


def data_dir() -> Path:
    env = os.environ.get("REACHDIRECT_OUTPUT_DIR")
    if env:
        return Path(env).expanduser()
    desktop = Path.home() / "Desktop"
    return desktop if desktop.is_dir() else Path.home() / "ReachDirect"


def state_dir() -> Path:
    return Path(os.environ.get("REACHDIRECT_STATE_DIR", Path.home() / ".reachdirect")).expanduser()


def daily_limit() -> int:
    try:
        return max(1, int(os.environ.get("REACHDIRECT_DAILY_LIMIT", "50")))
    except ValueError:
        return 50


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _quota_take(channel: str) -> str | None:
    """Counts today's sends per channel; returns an error message when the daily limit is reached."""
    path = state_dir() / "quota.json"
    today = date.today().isoformat()
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("date") != today:
        data = {"date": today}
    used = int(data.get(channel, 0))
    if used >= daily_limit():
        return f"Daily {channel} limit of {daily_limit()} reached (REACHDIRECT_DAILY_LIMIT). Try again tomorrow."
    data[channel] = used + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), "utf-8")
    return None


def _blocklist() -> DoNotContact:
    return DoNotContact(state_dir() / "do_not_contact.json")


def _log() -> OutreachLog:
    return OutreachLog(data_dir() / "outreach_contacts.xlsx")


def preview_message(
    template: str, recipient_name: str = "", company: str = "", extra: dict[str, str] | None = None
) -> str:
    """Fill {{first_name}}, {{name}}, {{company}} and any extra {{placeholders}} (fallbacks: {{first_name|there}})."""
    values = {
        "name": recipient_name,
        "first_name": first_name(recipient_name),
        "company": company,
        **(extra or {}),
    }
    text, missing = render(template, values)
    return _json({"message": text, "missing_placeholders": missing, "ready": not missing})


async def send_email(
    recipient_email: str,
    subject: str,
    message: str,
    sender_email: str,
    sender_name: str,
    recipient_name: str = "",
    reply_to: str | None = None,
    dry_run: bool = False,
) -> str:
    """Send one email through Brevo (needs BREVO_API_KEY and a sender verified in Brevo).

    Args:
        dry_run: Validate and return the payload without sending.
    """
    if _blocklist().blocked(recipient_email):
        return _json({"ok": False, "error": f"{recipient_email} is on the do-not-contact list."})
    _, missing = render(subject + "\n" + message, {})
    if missing:
        return _json(
            {
                "ok": False,
                "error": f"Unfilled placeholders: {', '.join(missing)}. Use preview_message first.",
            }
        )
    try:
        payload = mailer.build_payload(
            recipient_email, recipient_name, sender_email, sender_name, subject, message, reply_to
        )
    except mailer.EmailError as exc:
        return _json({"ok": False, "error": str(exc)})
    if dry_run:
        return _json({"ok": True, "dry_run": True, "payload": payload})
    if err := _quota_take("email"):
        return _json({"ok": False, "error": err})
    return _json(await mailer.send(payload, os.environ.get("BREVO_API_KEY", "")))


async def send_whatsapp(
    phone_number: str, message: str, default_region: str | None = None, ctx: Context | None = None
) -> str:
    """Send one WhatsApp message through WhatsApp Web (a browser window opens; first run asks for a QR scan).

    Args:
        phone_number: International format, e.g. "+90 532 123 45 67". National numbers need default_region.
        default_region: ISO country code used when the number has no + prefix, e.g. "TR".
    """
    try:
        digits = whatsapp.normalize_phone(phone_number, default_region)
    except whatsapp.PhoneError as exc:
        return _json({"ok": False, "error": str(exc)})
    if _blocklist().blocked(digits):
        return _json({"ok": False, "error": f"+{digits} is on the do-not-contact list."})
    if not message.strip():
        return _json({"ok": False, "error": "Message is empty."})
    _, missing = render(message, {})
    if missing:
        return _json(
            {
                "ok": False,
                "error": f"Unfilled placeholders: {', '.join(missing)}. Use preview_message first.",
            }
        )
    if err := _quota_take("whatsapp"):
        return _json({"ok": False, "error": err})

    async def log(text: str) -> None:
        if ctx:
            await ctx.info(text)

    result = await whatsapp.send_message(
        digits, message, state_dir() / "whatsapp-profile", data_dir(), log
    )
    return _json({**result, "to": f"+{digits}"})


def save_outreach_contact(
    name: str,
    email: str = "",
    phone: str = "",
    channel: str = "email",
    status: str = "contacted",
    company: str = "",
    notes: str = "",
) -> str:
    """Append a row to outreach_contacts.xlsx (Date, Name, Company, Email, Phone, Channel, Status, Notes)."""
    try:
        row = _log().add(name, email, phone, channel, status, company, notes)
    except (ValueError, OSError) as exc:
        return _json({"ok": False, "error": str(exc)})
    return _json({"ok": True, "saved": row, "file": str(_log().path)})


def list_outreach_contacts(limit: int = 50) -> str:
    """Latest rows of the outreach log."""
    rows = _log().rows()
    return _json({"file": str(_log().path), "total": len(rows), "rows": rows[-max(1, limit) :]})


def add_do_not_contact(email_or_phone: str) -> str:
    """Record that someone asked not to be contacted. Future sends to them are refused."""
    if not email_or_phone.strip():
        return _json({"ok": False, "error": "Give an email address or phone number."})
    _blocklist().add(email_or_phone)
    return _json({"ok": True, "blocked": email_or_phone.strip()})


for _fn in (
    preview_message,
    send_email,
    send_whatsapp,
    save_outreach_contact,
    list_outreach_contacts,
    add_do_not_contact,
):
    mcp.tool(_fn)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
