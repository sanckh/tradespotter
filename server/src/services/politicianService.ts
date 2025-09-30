import { supabase } from '../config/supabase';
import { Politician } from '../interfaces/Politician';
import { Trade } from '../interfaces/Trade';

export class PoliticianService {
  /**
   * Get all politicians ordered by last name
   */
  async getAllPoliticians(): Promise<Politician[]> {
    const { data, error } = await supabase
      .from('politicians')
      .select('*')
      .order('last_name', { ascending: true, nullsFirst: false });

    if (error) {
      throw new Error(`Failed to fetch politicians: ${error.message}`);
    }

    return data || [];
  }

  /**
   * Get recent trades with politician information
   */
  async getRecentTrades(limit: number = 20): Promise<Trade[]> {
    const { data, error } = await supabase
      .from('trades')
      .select(`
        *,
        politicians (
          id,
          full_name,
          state,
          chamber
        )
      `)
      .order('transaction_date', { ascending: false })
      .limit(limit);

    if (error) {
      throw new Error(`Failed to fetch trades: ${error.message}`);
    }

    return data || [];
  }

  /**
   * Get a politician by ID
   */
  async getPoliticianById(id: string): Promise<Politician | null> {
    const { data, error } = await supabase
      .from('politicians')
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        return null; // Not found
      }
      throw new Error(`Failed to fetch politician: ${error.message}`);
    }

    return data;
  }
}
