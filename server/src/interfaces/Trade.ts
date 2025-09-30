export interface Trade {
  id: string;
  amount_range: string | null;
  asset_name: string;
  created_at: string;
  disclosure_id: string;
  notes: string | null;
  politician_id: string;
  published_at: string | null;
  row_hash: string;
  side: string | null;
  ticker: string | null;
  transaction_date: string | null;
  updated_at: string;
  politicians?: {
    id: string;
    full_name: string;
    state: string | null;
    chamber: string | null;
  };
}
