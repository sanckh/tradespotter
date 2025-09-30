const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000/api';

export interface UserFollow {
  id: string;
  user_id: string;
  politician_id: string;
  created_at: string;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Get all politicians that a user is following
 */
export async function getUserFollows(userId: string): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/follows`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch user follows: ${response.statusText}`);
  }
  
  const result: ApiResponse<string[]> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch user follows');
  }
  
  return result.data;
}

/**
 * Follow a politician
 */
export async function followPolitician(userId: string, politicianId: string): Promise<UserFollow> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/follows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ politicianId }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to follow politician: ${response.statusText}`);
  }
  
  const result: ApiResponse<UserFollow> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to follow politician');
  }
  
  return result.data;
}

/**
 * Unfollow a politician
 */
export async function unfollowPolitician(userId: string, politicianId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/follows/${politicianId}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to unfollow politician: ${response.statusText}`);
  }
  
  const result: ApiResponse<void> = await response.json();
  
  if (!result.success) {
    throw new Error(result.error || 'Failed to unfollow politician');
  }
}

/**
 * Check if user is following a politician
 */
export async function checkFollowStatus(userId: string, politicianId: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/follows/${politicianId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to check follow status: ${response.statusText}`);
  }
  
  const result: ApiResponse<{ isFollowing: boolean }> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to check follow status');
  }
  
  return result.data.isFollowing;
}
