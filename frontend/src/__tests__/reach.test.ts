import { describe, expect, it } from 'vitest';
import { CONTACTS, TEMPLATES } from '../domain/seed';
import { firstName, normalizePhone, placeholders, render } from '../domain/templates';
import { MockOutreachService, blockKey } from '../services/OutreachService';
import { loadLog, logToCsv } from '../services/log';

describe('templates (mirrors tests/test_units.py)', () => {
  it('renders with fallbacks and reports missing', () => {
    expect(render('Hi {{ first_name | there }}, about {{company}} and {{deal}}', { company: 'Acme', first_name: ' ' }))
      .toEqual({ text: 'Hi there, about Acme and {{deal}}', missing: ['deal'] });
    expect(placeholders('{{a}} {{b|x}} {{a}}')).toEqual(['a', 'b']);
    expect(firstName('  Ayşe Yılmaz ')).toBe('Ayşe');
    expect(render('{{x|}}!', {}).text).toBe('!');
  });

  it('every bundled template renders fully for every contact', () => {
    for (const t of TEMPLATES) for (const c of CONTACTS) {
      const v = { name: c.name, first_name: firstName(c.name), company: c.company, city: c.city, sender_name: 'Me', product: '' };
      expect(render(t.subject + t.body, v).missing, `${t.id}/${c.id}`).toEqual([]);
    }
  });

  it('normalizes phones', () => {
    expect(normalizePhone('+44 20 7946 0958')).toBe('442079460958');
    expect(normalizePhone('0044 20 7946 0958')).toBe('442079460958');
    expect(normalizePhone('020 7946 0958')).toBeNull();
    expect(normalizePhone('+12')).toBeNull();
  });
});

describe('MockOutreachService', () => {
  it('validates, blocks and limits like the server', async () => {
    const blocked = new Set([blockKey('ANN@b.fi'), blockKey('+44 7946 095800')]);
    const svc = new MockOutreachService(() => blocked, 1, 0);
    expect(await svc.send({ channel: 'email', to: 'bad', subject: 's', body: 'b' })).toMatchObject({ ok: false });
    expect((await svc.send({ channel: 'email', to: 'ann@b.fi', subject: 's', body: 'b' })).ok).toBe(false);
    expect((await svc.send({ channel: 'whatsapp', to: '+447946095800', body: 'b' })).ok).toBe(false);
    expect((await svc.send({ channel: 'email', to: 'bo@b.fi', subject: '', body: 'b' })).ok).toBe(false);
    expect((await svc.send({ channel: 'email', to: 'bo@b.fi', subject: 's', body: 'Hi {{x}}' })).ok).toBe(false);
    expect((await svc.send({ channel: 'email', to: 'bo@b.fi', subject: 's', body: 'b' })).ok).toBe(true);
    const limited = await svc.send({ channel: 'email', to: 'cy@b.fi', subject: 's', body: 'b' });
    expect(limited.ok === false && limited.error).toContain('Daily email limit');
    expect((await svc.send({ channel: 'whatsapp', to: '+447946095801', body: 'b' })).ok).toBe(true);
  });
});

describe('log storage', () => {
  it('tolerates bad storage and escapes CSV', () => {
    const fake = { getItem: () => '{oops' } as unknown as Storage;
    expect(loadLog(fake)).toEqual([]);
    const csv = logToCsv([{ date: 'd', name: 'A, B', company: 'C', to: 't', channel: 'email', status: 'sent', notes: 'say "x"' }]);
    expect(csv.split('\n')[1]).toBe('d,"A, B",C,t,email,sent,"say ""x"""');
  });
});
