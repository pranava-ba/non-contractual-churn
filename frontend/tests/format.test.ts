import { describe, expect, it } from 'vitest';
import { QUALITY_HELP, QUALITY_LABEL, formatInt, formatMoney, formatNum, formatPct } from '../src/lib/format';

describe('format', () => {
  it('formats integers, money and percentages', () => {
    expect(formatInt(1234567)).toBe('1,234,567');
    expect(formatMoney(1234.5)).toBe('1,234.50');
    expect(formatPct(0.6234)).toBe('62.3%');
  });
  it('formats numbers to ~3 significant digits', () => {
    expect(formatNum(1.2345)).toBe('1.23');
    expect(formatNum(123.456)).toBe('123');
    expect(formatNum(0.012345)).toBe('0.0123');
    expect(formatNum(0)).toBe('0');
  });
  it('has a label and help text for every data-quality value', () => {
    for (const q of ['ok', 'insufficient_history', 'forecast_unavailable', 'clv_unavailable'] as const) {
      expect(QUALITY_LABEL[q]).toBeTruthy();
      expect(QUALITY_HELP[q]).toBeTruthy();
    }
  });
});
