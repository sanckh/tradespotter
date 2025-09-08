import express from 'express';
import cors from 'cors';

const app = express();

// Middlewares
app.use(cors());
app.use(express.json());

// Health check
app.get('/api/health', (_req: express.Request, res: express.Response) => {
  res.status(200).json({ status: 'ok' });
});

export default app;
