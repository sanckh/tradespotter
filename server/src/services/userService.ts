import { supabase } from '../config/supabase';
import { UserFollow } from '../interfaces/User';

export class UserService {
  /**
   * Get all politicians that a user is following
   */
  async getUserFollows(userId: string): Promise<string[]> {
    const { data, error } = await supabase
      .from('user_follows')
      .select('politician_id')
      .eq('user_id', userId);

    if (error) {
      throw new Error(`Failed to fetch user follows: ${error.message}`);
    }

    return data?.map(f => f.politician_id) || [];
  }

  /**
   * Follow a politician
   */
  async followPolitician(userId: string, politicianId: string): Promise<UserFollow> {
    const { data, error } = await supabase
      .from('user_follows')
      .insert([{
        user_id: userId,
        politician_id: politicianId
      }])
      .select()
      .single();

    if (error) {
      throw new Error(`Failed to follow politician: ${error.message}`);
    }

    return data;
  }

  /**
   * Unfollow a politician
   */
  async unfollowPolitician(userId: string, politicianId: string): Promise<void> {
    const { error } = await supabase
      .from('user_follows')
      .delete()
      .eq('user_id', userId)
      .eq('politician_id', politicianId);

    if (error) {
      throw new Error(`Failed to unfollow politician: ${error.message}`);
    }
  }

  /**
   * Check if user is following a politician
   */
  async isFollowing(userId: string, politicianId: string): Promise<boolean> {
    const { data, error } = await supabase
      .from('user_follows')
      .select('id')
      .eq('user_id', userId)
      .eq('politician_id', politicianId)
      .maybeSingle();

    if (error) {
      throw new Error(`Failed to check follow status: ${error.message}`);
    }

    return !!data;
  }
}
