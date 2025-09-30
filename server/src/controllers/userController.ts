import { Request, Response } from 'express';
import { UserService } from '../services/userService';

const userService = new UserService();

export class UserController {
  /**
   * GET /api/users/:userId/follows
   * Get all politicians that a user is following
   */
  async getUserFollows(req: Request, res: Response): Promise<void> {
    try {
      const { userId } = req.params;
      const follows = await userService.getUserFollows(userId);
      res.status(200).json({
        success: true,
        data: follows
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json({
        success: false,
        error: errorMessage
      });
    }
  }

  /**
   * POST /api/users/:userId/follows
   * Follow a politician
   */
  async followPolitician(req: Request, res: Response): Promise<void> {
    try {
      const { userId } = req.params;
      const { politicianId } = req.body;

      if (!politicianId) {
        res.status(400).json({
          success: false,
          error: 'politicianId is required'
        });
        return;
      }

      const follow = await userService.followPolitician(userId, politicianId);
      res.status(201).json({
        success: true,
        data: follow
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json({
        success: false,
        error: errorMessage
      });
    }
  }

  /**
   * DELETE /api/users/:userId/follows/:politicianId
   * Unfollow a politician
   */
  async unfollowPolitician(req: Request, res: Response): Promise<void> {
    try {
      const { userId, politicianId } = req.params;
      await userService.unfollowPolitician(userId, politicianId);
      res.status(200).json({
        success: true,
        message: 'Successfully unfollowed politician'
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json({
        success: false,
        error: errorMessage
      });
    }
  }

  /**
   * GET /api/users/:userId/follows/:politicianId
   * Check if user is following a politician
   */
  async checkFollowStatus(req: Request, res: Response): Promise<void> {
    try {
      const { userId, politicianId } = req.params;
      const isFollowing = await userService.isFollowing(userId, politicianId);
      res.status(200).json({
        success: true,
        data: { isFollowing }
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json({
        success: false,
        error: errorMessage
      });
    }
  }
}
