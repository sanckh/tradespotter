import { Router } from 'express';
import { PoliticianController } from '../controllers/politicianController';

const router = Router();
const politicianController = new PoliticianController();

// GET /api/politicians - Get all politicians
router.get('/', (req, res) => politicianController.getAllPoliticians(req, res));

// GET /api/politicians/trades - Get recent trades
router.get('/trades', (req, res) => politicianController.getRecentTrades(req, res));

// GET /api/politicians/:id - Get politician by ID
router.get('/:id', (req, res) => politicianController.getPoliticianById(req, res));

export default router;
