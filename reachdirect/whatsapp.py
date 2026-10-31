"""WhatsApp Web automation with Playwright. You log in once by scanning a QR code; the session is kept
in a persistent browser profile. Each call opens a chat and sends one message you approved."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import phonenumbers

INPUT_SELECTOR = 'footer div[contenteditable="true"]'
QR_SELECTOR = "canvas[aria-label], div[data-ref] canvas"
INVALID_SELECTOR = 'div[data-animate-modal-popup="true"]'

Log = Callable[[str], Awaitable[None]]


class PhoneError(ValueError):
    pass


def normalize_phone(raw: str, default_region: str | None = None) -> str:
    """Returns E.164 digits without '+', e.g. '+44 20 7946 0958' -> '442079460958'."""
    text = raw.strip()
    if text.startswith("00"):
        text = "+" + text[2:]
    try:
        number = phonenumbers.parse(
            text, None if text.startswith("+") else (default_region or "").upper() or None
        )
    except phonenumbers.NumberParseException as exc:
        raise PhoneError(
            f"Cannot read phone number {raw!r}. Use international format, e.g. +44 20 7946 0958."
        ) from exc
    if not phonenumbers.is_valid_number(number):
        raise PhoneError(f"{raw!r} is not a valid phone number.")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164).lstrip("+")


def chat_url(phone_digits: str, message: str) -> str:
    return f"https://web.whatsapp.com/send?phone={phone_digits}&text={quote(message, safe='')}"


def qr_viewer_html(image_name: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='2'>"
        "<title>WhatsApp login</title></head><body style='font-family:sans-serif;text-align:center;"
        "background:#f0f2f5;padding-top:40px'><h2>Scan with WhatsApp → Linked devices</h2>"
        "<p>This page refreshes every 2 seconds.</p>"
        f"<img src='{image_name}' style='border:12px solid #fff;border-radius:12px;max-width:360px'></body></html>"
    )


async def send_message(
    phone_digits: str,
    message: str,
    profile_dir: Path,
    qr_dir: Path,
    log: Log,
    login_timeout_s: int = 180,
) -> dict[str, Any]:
    try:
        from playwright.async_api import TimeoutError as PwTimeout
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "ok": False,
            "error": "Playwright is not installed. Run: pip install playwright && playwright install chromium",
        }

    profile_dir.mkdir(parents=True, exist_ok=True)
    channel = os.environ.get("REACHDIRECT_BROWSER_CHANNEL") or None  # e.g. "msedge" or "chrome"
    url = chat_url(phone_digits, message)
    qr_png, qr_page = qr_dir / "whatsapp_qr.png", qr_dir / "WhatsApp_Login.html"
    try:
        async with async_playwright() as pw:
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                channel=channel,
                viewport={"width": 1200, "height": 860},
            )
            try:
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_selector(
                    f"{QR_SELECTOR}, {INPUT_SELECTOR}", state="visible", timeout=60_000
                )

                if await page.locator(QR_SELECTOR).first.is_visible():
                    qr_dir.mkdir(parents=True, exist_ok=True)
                    qr_page.write_text(qr_viewer_html(qr_png.name), encoding="utf-8")
                    await log(f"WhatsApp needs a one-time login. Open {qr_page} and scan the code.")
                    for _ in range(login_timeout_s // 3):
                        qr = page.locator(QR_SELECTOR).first
                        if not await qr.is_visible():
                            break
                        await qr.screenshot(path=str(qr_png))
                        await page.wait_for_timeout(3000)
                    else:
                        return {
                            "ok": False,
                            "error": f"QR code not scanned within {login_timeout_s}s. Run again and scan.",
                        }
                    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

                try:
                    box = await page.wait_for_selector(
                        INPUT_SELECTOR, state="visible", timeout=45_000
                    )
                except PwTimeout:
                    if await page.locator(INVALID_SELECTOR).count():
                        return {"ok": False, "error": f"+{phone_digits} is not on WhatsApp."}
                    raise
                assert box is not None  # state="visible" never resolves to None
                await box.click()
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2500)
                return {"ok": True}
            finally:
                await ctx.close()
                for f in (qr_png, qr_page):
                    f.unlink(missing_ok=True)
    except PwTimeout:
        return {
            "ok": False,
            "error": "Timed out waiting for WhatsApp Web. Check your connection and try again.",
        }
    except Exception as exc:  # browser launch / navigation failures
        return {"ok": False, "error": f"WhatsApp automation failed: {exc}"}
