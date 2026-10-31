import json

import httpx
import pytest
import respx
from fastmcp import Client

from reachdirect import mailer, server


@pytest.fixture(autouse=True)
def dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("REACHDIRECT_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("REACHDIRECT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-test")
    monkeypatch.delenv("REACHDIRECT_DAILY_LIMIT", raising=False)


async def call(name, args):
    async with Client(server.mcp) as c:
        return json.loads((await c.call_tool(name, args)).content[0].text)


async def test_tools_registered():
    async with Client(server.mcp) as c:
        assert {t.name for t in await c.list_tools()} == {
            "preview_message",
            "send_email",
            "send_whatsapp",
            "save_outreach_contact",
            "list_outreach_contacts",
            "add_do_not_contact",
        }


async def test_preview():
    out = await call(
        "preview_message",
        {
            "template": "Hi {{first_name}} at {{company}}",
            "recipient_name": "Ann Lee",
            "company": "Acme",
        },
    )
    assert out == {"message": "Hi Ann at Acme", "missing_placeholders": [], "ready": True}


EMAIL = {
    "recipient_email": "ann@b.fi",
    "subject": "Hello",
    "message": "Hi Ann",
    "sender_email": "me@co.fi",
    "sender_name": "Me",
}


@respx.mock
async def test_send_email_success_and_dry_run():
    route = respx.post(mailer.BREVO_URL).mock(
        return_value=httpx.Response(201, json={"messageId": "<m1>"})
    )
    assert (await call("send_email", {**EMAIL, "dry_run": True}))["payload"]["to"][0][
        "email"
    ] == "ann@b.fi"
    assert not route.called
    assert await call("send_email", EMAIL) == {"ok": True, "message_id": "<m1>"}
    assert route.calls[0].request.headers["api-key"] == "xkeysib-test"


@respx.mock
async def test_send_email_errors(monkeypatch):
    respx.post(mailer.BREVO_URL).mock(
        return_value=httpx.Response(400, json={"message": "sender not valid"})
    )
    out = await call("send_email", EMAIL)
    assert not out["ok"] and "sender not valid" in out["error"] and "verified" in out["error"]
    assert (
        "Unfilled" in (await call("send_email", {**EMAIL, "message": "Hi {{first_name}}"}))["error"]
    )
    monkeypatch.setenv("BREVO_API_KEY", "")
    assert "BREVO_API_KEY" in (await call("send_email", EMAIL))["error"]


@respx.mock
async def test_do_not_contact_and_daily_limit(monkeypatch):
    respx.post(mailer.BREVO_URL).mock(return_value=httpx.Response(201, json={}))
    await call("add_do_not_contact", {"email_or_phone": "ANN@b.fi"})
    assert "do-not-contact" in (await call("send_email", EMAIL))["error"]
    monkeypatch.setenv("REACHDIRECT_DAILY_LIMIT", "1")
    other = {**EMAIL, "recipient_email": "bo@b.fi"}
    assert (await call("send_email", other))["ok"]
    assert "Daily email limit" in (await call("send_email", other))["error"]


async def test_whatsapp_validation_before_browser(monkeypatch):
    called = False

    async def fake_send(*a, **k):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr(server.whatsapp, "send_message", fake_send)
    assert (
        "Cannot read"
        in (await call("send_whatsapp", {"phone_number": "abc", "message": "hi"}))["error"]
    )
    assert (
        "empty"
        in (await call("send_whatsapp", {"phone_number": "+447946095800", "message": " "}))["error"]
    )
    await call("add_do_not_contact", {"email_or_phone": "+44 7946 095800"})
    assert (
        "do-not-contact"
        in (await call("send_whatsapp", {"phone_number": "+447946095800", "message": "hi"}))[
            "error"
        ]
    )
    assert not called
    assert await call("send_whatsapp", {"phone_number": "+447946095801", "message": "hi"}) == {
        "ok": True,
        "to": "+447946095801",
    }


async def test_log_tools():
    assert (await call("save_outreach_contact", {"name": "Ann", "email": "ann@b.fi"}))["ok"]
    assert not (await call("save_outreach_contact", {"name": " "}))["ok"]
    assert (await call("list_outreach_contacts", {}))["total"] == 1
