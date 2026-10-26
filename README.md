# ReachDirect MCP

**Live demo:** https://reach-direct-mcp.vercel.app (mock mode, nothing is sent)

An MCP server that lets Claude Desktop, Cursor or any MCP client do personal outreach for you: send an
email through Brevo, send a WhatsApp message through WhatsApp Web, and log every contact to an Excel
file. You state your name, sender address and message in the chat. Your assistant fills in the template,
shows you the final text, and sends it once you say yes.

| | |
|---|---|
| **MCP server** | Python 3.10+ · FastMCP · httpx (Brevo v3 API) · Playwright (WhatsApp Web) · openpyxl · phonenumbers |
| **Web demo** | React 18 · TypeScript · Tailwind CSS · Vite, deployed on Vercel |

---

## Tools

| Tool | What it does |
|---|---|
| `preview_message` | Fills `{{first_name}}`, `{{name}}`, `{{company}}` and any `{{custom}}` placeholder, with fallbacks such as `{{first_name\|there}}`. Lists anything still unfilled. |
| `send_email` | Sends one email through the Brevo transactional API over HTTPS. You need no SMTP setup or password, only `BREVO_API_KEY` and a sender address verified in Brevo. `dry_run=true` validates the email and returns it without sending. |
| `send_whatsapp` | Opens WhatsApp Web in a browser and sends one message. On first use, a QR code is saved as an auto-refreshing `WhatsApp_Login.html` in your output folder; scan it once and the session is kept. |
| `save_outreach_contact` | Appends Date, Name, Company, Email, Phone, Channel, Status and Notes to `outreach_contacts.xlsx`. |
| `list_outreach_contacts` | Shows the latest rows of the log. |
| `add_do_not_contact` | Records someone who asked not to be contacted. Later sends to that address or number are refused. |

Built-in safeguards:

- Messages with unfilled `{{placeholders}}` are refused.
- Email addresses are validated, and phone numbers must parse in international format.
- Sends are capped per channel per day (`REACHDIRECT_DAILY_LIMIT`, default 50).
- WhatsApp messages are URL-encoded, so `&`, `#` and line breaks arrive intact.

---

## Install

```bash
git clone https://github.com/weblinkify/reach-direct-mcp
cd reach-direct-mcp
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
playwright install chromium
```

MCP client config:

```json
{
  "mcpServers": {
    "reachdirect": {
      "command": "/ABSOLUTE/PATH/reach-direct-mcp/.venv/bin/reachdirect",
      "env": {
        "BREVO_API_KEY": "xkeysib-your-key",
        "REACHDIRECT_OUTPUT_DIR": "~/Desktop",
        "REACHDIRECT_DAILY_LIMIT": "50"
      }
    }
  }
}
```

| Variable | Default | Purpose |
|---|---|---|
| `BREVO_API_KEY` | — | Brevo → Settings → SMTP & API → API keys. The free plan sends 300 emails/day. |
| `REACHDIRECT_OUTPUT_DIR` | Desktop, else `~/ReachDirect` | `outreach_contacts.xlsx` and the WhatsApp QR page. |
| `REACHDIRECT_STATE_DIR` | `~/.reachdirect` | WhatsApp browser profile, daily counters, do-not-contact list. |
| `REACHDIRECT_DAILY_LIMIT` | `50` | Max sends per channel per day. |
| `REACHDIRECT_BROWSER_CHANNEL` | bundled Chromium | Use `msedge` or `chrome` to drive an installed browser instead. |

Before the first email, verify your sender address or domain in Brevo (Senders, domains & IPs) and set
up SPF/DKIM. Otherwise Brevo rejects the send, and the tool tells you why.

### Example prompt

```text
I'm Daniel Weber (daniel@weber-parts.example). Write to Marie Laurent
(marie.laurent@laurent-remorques.example, +33 6 12 34 56 78) at Laurent Remorques
about our trailer axle range.
1. preview_message with a short intro, then show me the text.
2. After I approve: send_email, then send_whatsapp with a one-line heads-up.
3. save_outreach_contact for Marie with channel "email+whatsapp".
```

---

## Web demo

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

You can pick a fictional contact and a template, edit the placeholders and see the email or WhatsApp
preview. A mock "send" applies the same validation, do-not-contact and daily-limit rules as the server
and logs the attempt. Nothing leaves the browser.

**Vercel:** import the repo and set **Root Directory** to `frontend`; `frontend/vercel.json` does the rest.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q                 # Brevo calls are mocked; the WhatsApp browser flow is not run in tests
cd frontend && npm test && npm run build
```

## Responsible use

Send one-to-one messages to people with a reason to hear from you, honour opt-outs (`add_do_not_contact`)
and follow the rules where you operate (GDPR / ePrivacy, CAN-SPAM, KVKK). WhatsApp's terms restrict
automated and bulk messaging; misuse can get your number banned. This tool sends one approved message
per call on purpose.

## License

MIT
