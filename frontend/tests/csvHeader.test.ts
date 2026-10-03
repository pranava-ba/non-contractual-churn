import { describe, expect, it } from 'vitest';
import { parseHeaderLine, validateFile, validateHeader } from '../src/lib/csvHeader';

describe('parseHeaderLine', () => {
  it('splits the first line only', () => {
    expect(parseHeaderLine('customer_id,transaction_date,amount\n1,2024-01-01,5\n')).toEqual([
      'customer_id', 'transaction_date', 'amount'
    ]);
  });
  it('strips a UTF-8 BOM and handles CRLF', () => {
    expect(parseHeaderLine('﻿customer_id,transaction_date\r\n1,2024-01-01')).toEqual([
      'customer_id', 'transaction_date'
    ]);
  });
  it('handles quoted fields containing commas and escaped quotes', () => {
    expect(parseHeaderLine('"a,b","say ""hi""",c')).toEqual(['a,b', 'say "hi"', 'c']);
  });
  it('returns a single empty column for empty input', () => {
    expect(parseHeaderLine('')).toEqual(['']);
  });
});

describe('validateHeader', () => {
  it('accepts the required columns, with or without amount, in any order', () => {
    expect(validateHeader(['transaction_date', 'customer_id'])).toMatchObject({ ok: true, hasAmount: false });
    expect(validateHeader(['customer_id', 'transaction_date', 'amount', 'extra'])).toMatchObject({
      ok: true, hasAmount: true
    });
  });
  it('reports each missing required column', () => {
    const r = validateHeader(['foo', 'bar']);
    expect(r.ok).toBe(false);
    expect(r.errors).toEqual([
      'Missing required column "customer_id".',
      'Missing required column "transaction_date".'
    ]);
  });
  it('hints when a column differs only by case (the server is case-sensitive)', () => {
    const r = validateHeader(['Customer_ID', 'transaction_date']);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toBe(
      'Found "Customer_ID" — column names are case-sensitive; rename it to "customer_id".'
    );
  });
});

describe('validateFile', () => {
  const csv = (text: string, name = 'log.csv') => new File([text], name, { type: 'text/csv' });

  it('passes a good file', async () => {
    expect((await validateFile(csv('customer_id,transaction_date\n1,2024-01-01\n'))).ok).toBe(true);
  });
  it('rejects an empty file', async () => {
    const r = await validateFile(csv(''));
    expect(r.ok).toBe(false);
    expect(r.errors).toEqual(['The file is empty.']);
  });
  it('rejects a non-CSV file by extension', async () => {
    const r = await validateFile(new File(['customer_id,transaction_date'], 'log.xlsx'));
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toBe('Please choose a .csv file.');
  });
  it('rejects a file with a bad header', async () => {
    const r = await validateFile(csv('id,date\n1,2024-01-01\n'));
    expect(r.ok).toBe(false);
    expect(r.errors).toHaveLength(2);
  });
});
