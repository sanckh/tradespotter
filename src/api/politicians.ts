const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000/api';

export interface Politician {
  id: string;
  bioguide_id: string | null;
  chamber: string | null;
  created_at: string;
  district: string | null;
  external_ids: Record<string, unknown>;
  first_name: string | null;
  full_name: string;
  last_name: string | null;
  state: string | null;
  updated_at: string;
}

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

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Fetch all politicians
 */
export async function getAllPoliticians(): Promise<Politician[]> {
  const response = await fetch(`${API_BASE_URL}/politicians`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch politicians: ${response.statusText}`);
  }
  
  const result: ApiResponse<Politician[]> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch politicians');
  }
  
  return result.data;
}

/**
 * Fetch recent trades with politician information
 */
export async function getRecentTrades(limit: number = 20): Promise<Trade[]> {
  const response = await fetch(`${API_BASE_URL}/politicians/trades?limit=${limit}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch trades: ${response.statusText}`);
  }
  
  const result: ApiResponse<Trade[]> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch trades');
  }
  
  return result.data;
}

/**
 * Fetch a politician by ID
 */
export async function getPoliticianById(id: string): Promise<Politician> {
  const response = await fetch(`${API_BASE_URL}/politicians/${id}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch politician: ${response.statusText}`);
  }
  
  const result: ApiResponse<Politician> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch politician');
  }
  
  return result.data;
}
