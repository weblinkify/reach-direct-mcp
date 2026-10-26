import { Ban, Download, Github, Mail, MessageCircle, Send } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { CONTACTS, TEMPLATES, type Channel, type Contact } from './domain/seed';
import { firstName, render } from './domain/templates';
import { downloadText } from './download';
import { loadDnc, loadLog, logToCsv, saveDnc, saveLog, type LogRow } from './services/log';
import { MockOutreachService, blockKey } from './services/OutreachService';

const now = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

export default function App() {
  const [contactId, setContactId] = useState(CONTACTS[0].id);
  const [channel, setChannel] = useState<Channel>('email');
  const [templateId, setTemplateId] = useState(TEMPLATES[0].id);
  const [subject, setSubject] = useState(TEMPLATES[0].subject);
  const [body, setBody] = useState(TEMPLATES[0].body);
  const [senderName, setSenderName] = useState('Daniel Weber');
  const [product, setProduct] = useState('');
  const [log, setLog] = useState<LogRow[]>(() => loadLog());
  const [dnc, setDnc] = useState<string[]>(() => loadDnc());
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => saveLog(log), [log]);
  useEffect(() => saveDnc(dnc), [dnc]);

  const dncSet = useMemo(() => new Set(dnc), [dnc]);
  const dncRef = useRef(dncSet);
  dncRef.current = dncSet;
  // One service for the session so its daily counter persists; it reads the latest do-not-contact list.
  const service = useMemo(() => new MockOutreachService(() => dncRef.current), []);
  const contact = CONTACTS.find((c) => c.id === contactId) as Contact;
  const to = channel === 'email' ? contact.email : contact.phone;
  const values = { name: contact.name, first_name: firstName(contact.name), company: contact.company, city: contact.city,
    sender_name: senderName, product };
  const subj = render(subject, values);
  const msg = render(body, values);
  const missing = [...new Set([...(channel === 'email' ? subj.missing : []), ...msg.missing])];
  const isBlocked = (c: Contact) => dncSet.has(blockKey(c.email)) || (c.phone && dncSet.has(blockKey(c.phone)));

  const pickTemplate = (id: string) => {
    const t = TEMPLATES.find((x) => x.id === id)!;
    setTemplateId(id);
    setSubject(t.subject);
    setBody(t.body);
    if (id === 'whatsapp') setChannel('whatsapp');
  };

  const send = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const res = await service.send({ channel, to, subject: subj.text, body: msg.text });
      setLog((cur) => [{ date: now(), name: contact.name, company: contact.company, to, channel,
        status: res.ok ? 'sent' : 'failed', notes: res.ok ? res.id : res.error }, ...cur]);
      setNotice(res.ok ? { ok: true, text: `Sent to ${to} (mock). Logged.` } : { ok: false, text: res.error });
    } finally {
      setBusy(false);
    }
  };

  const toggleDnc = (c: Contact) => {
    const keys = [blockKey(c.email), ...(c.phone ? [blockKey(c.phone)] : [])];
    setDnc((cur) => (isBlocked(c) ? cur.filter((k) => !keys.includes(k)) : [...new Set([...cur, ...keys])]));
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-white"><Send size={19} /></div>
            <div>
              <h1 className="text-lg font-bold leading-tight">ReachDirect</h1>
              <p className="text-xs text-slate-500">Personal outreach · Brevo email · WhatsApp Web · outreach log</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="chip bg-amber-100 text-amber-800" title="Nothing is sent. Contacts are fictional.">Demo · nothing is sent</span>
            <a className="btn-ghost" href="https://github.com/weblinkify/reach-direct-mcp" target="_blank" rel="noreferrer"><Github size={16} /> MCP server</a>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-6 lg:grid-cols-[300px_1fr]">
        <aside className="card h-fit p-3" aria-label="Contacts">
          <h2 className="label px-1">Contacts</h2>
          <ul className="space-y-1">
            {CONTACTS.map((c) => (
              <li key={c.id}>
                <button type="button" onClick={() => setContactId(c.id)} aria-current={c.id === contactId}
                  className={`w-full rounded-lg px-3 py-2 text-left ${c.id === contactId ? 'bg-brand-soft ring-1 ring-brand/30' : 'hover:bg-slate-50'}`}>
                  <p className="flex items-center gap-1.5 font-medium">{c.name}
                    {isBlocked(c) && <span className="chip bg-rose-100 text-rose-700">do not contact</span>}</p>
                  <p className="text-xs text-slate-500">{c.company} · {c.city}</p>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="min-w-0 space-y-4">
          <section className="card space-y-3 p-4" aria-labelledby="compose-h">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="compose-h" className="font-semibold">Compose for {contact.name}</h2>
              <div className="flex gap-1 rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Channel">
                {(['email', 'whatsapp'] as const).map((ch) => (
                  <button key={ch} type="button" role="radio" aria-checked={channel === ch} onClick={() => setChannel(ch)}
                    className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${channel === ch ? 'bg-white shadow-sm' : 'text-slate-500'}`}>
                    {ch === 'email' ? <Mail size={15} /> : <MessageCircle size={15} />} {ch === 'email' ? 'Email' : 'WhatsApp'}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="label" htmlFor="tpl">Template</label>
                <select id="tpl" className="input" value={templateId} onChange={(e) => pickTemplate(e.target.value)}>
                  {TEMPLATES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="sender">Your name</label>
                <input id="sender" className="input" value={senderName} onChange={(e) => setSenderName(e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="product">{'{{product}}'}</label>
                <input id="product" className="input" placeholder="uses the template fallback" value={product} onChange={(e) => setProduct(e.target.value)} />
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                {channel === 'email' && (
                  <div>
                    <label className="label" htmlFor="subject">Subject template</label>
                    <input id="subject" className="input font-mono text-[13px]" value={subject} onChange={(e) => setSubject(e.target.value)} />
                  </div>
                )}
                <div>
                  <label className="label" htmlFor="body">Message template</label>
                  <textarea id="body" className="input min-h-[220px] font-mono text-[13px]" value={body} onChange={(e) => setBody(e.target.value)} />
                </div>
                <p className="text-xs text-slate-500">Placeholders: {'{{first_name}} {{name}} {{company}} {{city}} {{sender_name}} {{product}}'} · fallback: {'{{first_name|there}}'}</p>
              </div>
              <div>
                <p className="label">Preview → {to || <span className="text-rose-600">no {channel === 'email' ? 'email' : 'phone'}</span>}</p>
                {channel === 'email' ? (
                  <div className="rounded-lg border border-slate-200">
                    <p className="border-b border-slate-200 px-3 py-2 text-sm"><span className="text-slate-500">Subject:</span> <strong>{subj.text}</strong></p>
                    <p className="whitespace-pre-wrap px-3 py-3 text-sm leading-relaxed">{msg.text}</p>
                  </div>
                ) : (
                  <div className="rounded-lg bg-[#efeae2] p-4">
                    <p className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg rounded-tr-none bg-[#d9fdd3] px-3 py-2 text-sm shadow-sm">{msg.text}</p>
                  </div>
                )}
                {missing.length > 0 && <p className="mt-2 text-sm text-rose-700">Unfilled: {missing.join(', ')}</p>}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button type="button" className="btn-primary" disabled={busy || !to || missing.length > 0} onClick={send}>
                    <Send size={15} /> {busy ? 'Sending…' : channel === 'email' ? 'Send via Brevo' : 'Send on WhatsApp'}
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => toggleDnc(contact)}>
                    <Ban size={15} /> {isBlocked(contact) ? 'Allow contact again' : 'Mark do-not-contact'}
                  </button>
                </div>
                {notice && <p role="status" className={`mt-2 text-sm ${notice.ok ? 'text-emerald-700' : 'text-rose-700'}`}>{notice.text}</p>}
              </div>
            </div>
          </section>

          <section className="card p-4" aria-labelledby="log-h">
            <div className="mb-2 flex items-center justify-between">
              <h2 id="log-h" className="font-semibold">Outreach log <span className="text-slate-400">({log.length})</span></h2>
              <div className="flex gap-2">
                <button type="button" className="btn-ghost" disabled={!log.length} onClick={() => setLog([])}>Clear</button>
                <button type="button" className="btn-ghost" disabled={!log.length} onClick={() => downloadText('outreach_contacts.csv', logToCsv(log), 'text/csv')}>
                  <Download size={15} /> CSV
                </button>
              </div>
            </div>
            {log.length === 0 ? <p className="text-sm text-slate-500">Every send is logged here. The MCP server writes the same rows to outreach_contacts.xlsx.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr><th className="py-1.5">Date</th><th>Name</th><th>To</th><th>Channel</th><th>Status</th><th>Notes</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {log.map((r, i) => (
                      <tr key={`${r.date}-${i}`}>
                        <td className="whitespace-nowrap py-2 tabular-nums text-slate-500">{r.date}</td>
                        <td className="font-medium">{r.name}</td>
                        <td className="font-mono text-[12px]">{r.to}</td>
                        <td>{r.channel}</td>
                        <td><span className={`chip ${r.status === 'sent' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-700'}`}>{r.status}</span></td>
                        <td className="max-w-[260px] truncate text-slate-500" title={r.notes}>{r.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </main>
      <footer className="pb-8 text-center text-xs text-slate-400">Demo: nothing leaves your browser. The MCP server sends through Brevo and WhatsApp Web after you approve each message.</footer>
    </div>
  );
}
