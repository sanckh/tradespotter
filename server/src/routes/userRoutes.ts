import { Router } from 'express';
import { UserController } from '../controllers/userController';

const router = Router();
const userController = new UserController();

// GET /api/users/:userId/follows - Get all politicians user is following
router.get('/:userId/follows', (req, res) => userController.getUserFollows(req, res));

// POST /api/users/:userId/follows - Follow a politician
router.post('/:userId/follows', (req, res) => userController.followPolitician(req, res));

// DELETE /api/users/:userId/follows/:politicianId - Unfollow a politician
router.delete('/:userId/follows/:politicianId', (req, res) => userController.unfollowPolitician(req, res));

// GET /api/users/:userId/follows/:politicianId - Check if following
router.get('/:userId/follows/:politicianId', (req, res) => userController.checkFollowStatus(req, res));

export default router;
