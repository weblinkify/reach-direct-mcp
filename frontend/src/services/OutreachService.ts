import { isEmail, normalizePhone } from '../domain/templates';
import type { Channel } from '../domain/seed';

export interface SendRequest {
  channel: Channel;
  to: string;
  subject?: string;
  body: string;
}

export type SendResult = { ok: true; id: string } | { ok: false; error: string };

export interface OutreachService {
  send(req: SendRequest): Promise<SendResult>;
}

/** Mock of the MCP server's send_email / send_whatsapp: same validation, do-not-contact and daily-limit rules,
 * nothing leaves the browser. */
export class MockOutreachService implements OutreachService {
  private sent: Record<Channel, number> = { email: 0, whatsapp: 0 };

  constructor(
    private readonly blocked: () => Set<string>,
    private readonly dailyLimit = 50,
    private readonly latencyMs = 700,
  ) {}

  async send(req: SendRequest): Promise<SendResult> {
    if (this.latencyMs) await new Promise((r) => setTimeout(r, this.latencyMs));
    const key = blockKey(req.to);
    if (req.channel === 'email' && !isEmail(req.to)) return { ok: false, error: `Invalid email address: ${req.to}` };
    if (req.channel === 'whatsapp' && !normalizePhone(req.to)) {
      return { ok: false, error: 'Phone must be in international format, e.g. +44 20 7946 0958.' };
    }
    if (this.blocked().has(key)) return { ok: false, error: `${req.to} is on the do-not-contact list.` };
    if (/\{\{/.test(`${req.subject ?? ''}${req.body}`)) return { ok: false, error: 'Fill every {{placeholder}} before sending.' };
    if (req.channel === 'email' && !req.subject?.trim()) return { ok: false, error: 'Subject is empty.' };
    if (!req.body.trim()) return { ok: false, error: 'Message is empty.' };
    if (this.sent[req.channel] >= this.dailyLimit) {
      return { ok: false, error: `Daily ${req.channel} limit of ${this.dailyLimit} reached.` };
    }
    this.sent[req.channel] += 1;
    return { ok: true, id: req.channel === 'email' ? `<mock-${Date.now()}@smtp-relay.brevo.example>` : `wa-${Date.now()}` };
  }
}

export function blockKey(value: string): string {
  const v = value.trim().toLowerCase();
  return v.includes('@') ? v : v.replace(/\D/g, '');
}
