/** Browser port of reachdirect/templates.py. */
const PLACEHOLDER = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\|\s*([^}]*?)\s*)?\}\}/g;

export function placeholders(template: string): string[] {
  return [...new Set([...template.matchAll(PLACEHOLDER)].map((m) => m[1]))];
}

export function render(template: string, values: Record<string, string | undefined>): { text: string; missing: string[] } {
  const missing: string[] = [];
  const text = template.replace(PLACEHOLDER, (whole, key: string, fallback?: string) => {
    const value = values[key];
    if (value != null && value.trim()) return value.trim();
    if (fallback !== undefined) return fallback;
    missing.push(key);
    return whole;
  });
  return { text, missing: [...new Set(missing)] };
}

export const firstName = (full: string) => full.trim().split(/\s+/)[0] ?? '';

export function normalizePhone(raw: string): string | null {
  let t = raw.trim();
  if (t.startsWith('00')) t = `+${t.slice(2)}`;
  if (!t.startsWith('+')) return null;
  const digits = t.replace(/\D/g, '');
  return digits.length >= 8 && digits.length <= 15 ? digits : null;
}

export const isEmail = (s: string) => /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}$/.test(s.trim());
