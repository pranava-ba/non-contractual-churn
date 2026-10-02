export type JobStatus = 'queued' | 'running' | 'done' | 'failed';
export type DataQuality = 'ok' | 'insufficient_history' | 'forecast_unavailable' | 'clv_unavailable';

export interface JobInfo {
  id: string;
  status: JobStatus;
  error_reason: string | null;
}

export interface CustomerRow {
  customer_id: string;
  expected_purchases: number;
  p_alive: number;
  clv_point: number;
  clv_lower: number;
  clv_upper: number;
  data_quality: DataQuality;
}

export type SortKey = 'customer_id' | 'expected_purchases' | 'p_alive' | 'clv_point' | 'data_quality';

export interface ResultsQuery {
  page: number;
  pageSize: number;
  sort: SortKey;
  order: 'asc' | 'desc';
  quality: DataQuality | '';
  q: string;
}

export interface ResultsPage {
  job_id: string;
  page: number;
  page_size: number;
  total: number;
  customers: CustomerRow[];
}

export interface Histogram {
  edges: number[];
  counts: number[];
}

export interface JobSummary {
  job_id: string;
  n_customers: number;
  quality_counts: Partial<Record<DataQuality, number>>;
  mean_p_alive: number;
  total_expected_purchases: number;
  total_clv: number;
  has_clv_interval: boolean;
  histograms: { p_alive: Histogram; expected_purchases: Histogram; clv_point: Histogram };
}
