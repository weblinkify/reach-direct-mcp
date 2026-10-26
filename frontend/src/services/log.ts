import type { Channel } from '../domain/seed';

export interface LogRow {
  date: string;
  name: string;
  company: string;
  to: string;
  channel: Channel;
  status: 'sent' | 'failed';
  notes: string;
}

const LOG_KEY = 'reachdirect.log.v1';
const DNC_KEY = 'reachdirect.dnc.v1';

function storage(): Storage | undefined {
  try {
    return typeof window !== 'undefined' ? window.localStorage : undefined;
  } catch {
    return undefined;
  }
}

function read<T>(key: string, guard: (v: unknown) => v is T, s = storage()): T[] {
  try {
    const parsed: unknown = JSON.parse(s?.getItem(key) ?? '[]');
    return Array.isArray(parsed) ? parsed.filter(guard) : [];
  } catch {
    return [];
  }
}

function write(key: string, value: unknown, s = storage()) {
  try {
    s?.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: keep in memory */
  }
}

const isRow = (v: unknown): v is LogRow =>
  typeof (v as LogRow)?.name === 'string' && typeof (v as LogRow)?.to === 'string' &&
  ((v as LogRow).channel === 'email' || (v as LogRow).channel === 'whatsapp');

export const loadLog = (s?: Storage) => read(LOG_KEY, isRow, s ?? storage());
export const saveLog = (rows: LogRow[], s?: Storage) => write(LOG_KEY, rows, s ?? storage());
export const loadDnc = (s?: Storage) => read(DNC_KEY, (v): v is string => typeof v === 'string', s ?? storage());
export const saveDnc = (items: string[], s?: Storage) => write(DNC_KEY, items, s ?? storage());

export function logToCsv(rows: LogRow[]): string {
  const cell = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  return ['date,name,company,to,channel,status,notes',
    ...rows.map((r) => [r.date, r.name, r.company, r.to, r.channel, r.status, r.notes].map(cell).join(','))].join('\n') + '\n';
}
