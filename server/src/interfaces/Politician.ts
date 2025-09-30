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
