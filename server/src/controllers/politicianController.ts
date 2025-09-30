import { Request, Response } from 'express';
import { PoliticianService } from '../services/politicianService';

const politicianService = new PoliticianService();

export class PoliticianController {
  /**
   * GET /api/politicians
   * Get all politicians
   */
  async getAllPoliticians(req: Request, res: Response): Promise<void> {
    try {
      const politicians = await politicianService.getAllPoliticians();
      res.status(200).json({
        success: true,
        data: politicians
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
   * GET /api/politicians/trades
   * Get recent trades with politician information
   */
  async getRecentTrades(req: Request, res: Response): Promise<void> {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string, 10) : 20;
      const trades = await politicianService.getRecentTrades(limit);
      res.status(200).json({
        success: true,
        data: trades
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
   * GET /api/politicians/:id
   * Get a politician by ID
   */
  async getPoliticianById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const politician = await politicianService.getPoliticianById(id);
      
      if (!politician) {
        res.status(404).json({
          success: false,
          error: 'Politician not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: politician
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
