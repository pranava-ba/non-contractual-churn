// Mirrors the server's schema check (cpp/src/ingest.cpp): required columns are exact,
// case-sensitive names; `amount` is optional. This only exists to fail fast, before a
// potentially huge upload -- the server stays the source of truth.
const REQUIRED = ['customer_id', 'transaction_date'] as const;
const HEADER_BYTES = 64 * 1024;

export interface HeaderCheck {
  ok: boolean;
  errors: string[];
  hasAmount: boolean;
  columns: string[];
}

export function parseHeaderLine(text: string): string[] {
  const line = text.replace(/^﻿/, '').split(/\r\n|\n|\r/, 1)[0] ?? '';
  const cols: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else inQuotes = false;
      } else cur += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ',') {
      cols.push(cur);
      cur = '';
    } else cur += ch;
  }
  cols.push(cur);
  return cols;
}

export function validateHeader(columns: string[]): HeaderCheck {
  const errors: string[] = [];
  for (const name of REQUIRED) {
    if (columns.includes(name)) continue;
    const near = columns.find((c) => c.trim().toLowerCase() === name);
    errors.push(
      near !== undefined
        ? `Found "${near}" — column names are case-sensitive; rename it to "${name}".`
        : `Missing required column "${name}".`
    );
  }
  return { ok: errors.length === 0, errors, hasAmount: columns.includes('amount'), columns };
}

function readSlice(file: File, bytes: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file.slice(0, bytes));
  });
}

export async function validateFile(file: File): Promise<HeaderCheck> {
  const fail = (msg: string): HeaderCheck => ({ ok: false, errors: [msg], hasAmount: false, columns: [] });
  if (file.size === 0) return fail('The file is empty.');
  if (!/\.csv$/i.test(file.name) && file.type !== 'text/csv') return fail('Please choose a .csv file.');
  return validateHeader(parseHeaderLine(await readSlice(file, HEADER_BYTES)));
}
