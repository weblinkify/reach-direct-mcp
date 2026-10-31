from datetime import datetime

import pytest

from reachdirect import mailer, whatsapp
from reachdirect.templates import first_name, placeholders, render
from reachdirect.tracker import DoNotContact, OutreachLog


def test_render_with_fallbacks_and_missing():
    text, missing = render(
        "Hi {{ first_name | there }}, about {{company}} and {{deal}}",
        {"company": "Acme", "first_name": " "},
    )
    assert text == "Hi there, about Acme and {{deal}}" and missing == ["deal"]
    assert placeholders("{{a}} {{b|x}} {{a}}") == ["a", "b"]
    assert first_name("  Ayşe Yılmaz ") == "Ayşe" and first_name("") == ""


def test_text_to_html_escapes_and_keeps_breaks():
    assert (
        mailer.text_to_html("Hi <b>\nline2\n\nP2 & co")
        == "<p>Hi &lt;b&gt;<br>line2</p><p>P2 &amp; co</p>"
    )


def test_build_payload_validates():
    p = mailer.build_payload("a@b.fi", "Ann", "me@co.fi", "Me", "Hello", "Body", reply_to="r@co.fi")
    assert p["to"] == [{"email": "a@b.fi", "name": "Ann"}] and p["replyTo"] == {"email": "r@co.fi"}
    assert (
        mailer.build_payload("a@b.fi", None, "me@co.fi", "", "S", "B")["sender"]["name"]
        == "me@co.fi"
    )
    for args in [
        ("bad", None, "me@co.fi", "Me", "S", "B"),
        ("a@b.fi", None, "x", "Me", "S", "B"),
        ("a@b.fi", None, "me@co.fi", "Me", " ", "B"),
        ("a@b.fi", None, "me@co.fi", "Me", "S", ""),
    ]:
        with pytest.raises(mailer.EmailError):
            mailer.build_payload(*args)


def test_phone_normalization_and_url():
    assert whatsapp.normalize_phone("+44 20 7946 0958") == "442079460958"
    assert whatsapp.normalize_phone("0044 20 7946 0958") == "442079460958"
    assert whatsapp.normalize_phone("0532 123 45 67", "tr") == "905321234567"
    for bad in ("12", "hello", "0532 123 45 67"):
        with pytest.raises(whatsapp.PhoneError):
            whatsapp.normalize_phone(bad)
    assert (
        whatsapp.chat_url("4420", "Hi & bye #1?")
        == "https://web.whatsapp.com/send?phone=4420&text=Hi%20%26%20bye%20%231%3F"
    )


def test_outreach_log_roundtrip(tmp_path):
    log = OutreachLog(tmp_path / "o.xlsx")
    assert log.rows() == []
    log.add("Ann Lee", "ann@b.fi", channel="email", when=datetime(2026, 10, 1, 9, 30))
    log.add("Bo", phone="+358401234567", channel="whatsapp", notes="follow up")
    rows = log.rows()
    assert rows[0]["Date"] == "2026-10-01 09:30" and rows[0]["Email"] == "ann@b.fi"
    assert rows[1]["Channel"] == "whatsapp" and rows[1]["Notes"] == "follow up"
    with pytest.raises(ValueError):
        log.add("  ")


def test_do_not_contact(tmp_path):
    dnc = DoNotContact(tmp_path / "dnc.json")
    assert not dnc.blocked("a@b.fi")
    dnc.add("A@B.fi ")
    dnc.add("+358 40 123 4567")
    assert dnc.blocked("a@b.fi") and dnc.blocked("358401234567") and not dnc.blocked("")
    (tmp_path / "dnc.json").write_text("{corrupt")
    assert not dnc.blocked("a@b.fi")
