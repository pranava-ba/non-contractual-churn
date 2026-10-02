import type { DataQuality } from './types';

const int = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const money = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sig3 = new Intl.NumberFormat('en-US', { maximumSignificantDigits: 3 });

export const formatInt = (n: number) => int.format(n);
export const formatMoney = (n: number) => money.format(n);
export const formatPct = (p: number) => `${(p * 100).toFixed(1)}%`;
export const formatNum = (n: number) => sig3.format(n);

export const QUALITY_LABEL: Record<DataQuality, string> = {
  ok: 'OK',
  insufficient_history: 'Low history',
  forecast_unavailable: 'No forecast',
  clv_unavailable: 'No CLV'
};

export const QUALITY_HELP: Record<DataQuality, string> = {
  ok: 'Full forecast and CLV.',
  insufficient_history:
    'Only one purchase on record, so the forecast is low-confidence. Any CLV shown rests on the cohort-wide average spend.',
  forecast_unavailable:
    'The forecast could not be computed for this customer. Values are shown as 0 and are not predictions.',
  clv_unavailable:
    'The forecast is fine, but spend per order is too uncertain to estimate CLV. CLV is shown as 0 and is not a prediction.'
};
