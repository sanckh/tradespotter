import dotenv from 'dotenv';
dotenv.config();

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import politicianRoutes from './routes/politicianRoutes';
import userRoutes from './routes/userRoutes';

const app = express();
const port = Number(process.env.PORT) || 4000;

// Rate limiting
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,  // 1 minute window
  max: 100,             // Max 100 requests per minute
  message: 'Too many requests. Please try again later.',
});

// Allowed origins for CORS
const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:3000',
  'http://localhost:8080',
  'http://localhost:8081',
  process.env.FRONTEND_URL,
].filter(Boolean) as string[];

// CORS configuration
const corsOptions: Parameters<typeof cors>[0] = {
  origin: (origin: string | undefined, callback: (err: Error | null, allow?: boolean) => void) => {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      callback(null, true); // Allow request
    } else {
      callback(new Error(`CORS policy does not allow access from origin: ${origin}`), false); // Block request
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'credentials', 'X-Requested-With'],
  exposedHeaders: ['Content-Type', 'Authorization'],
  preflightContinue: false,
  optionsSuccessStatus: 204
};

// Apply middleware
app.use(cors(corsOptions));
app.use(apiLimiter);
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path} ${res.statusCode} - ${duration}ms`);
  });
  next();
});

// Health check
app.get('/api/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// API Routes
app.use('/api/politicians', politicianRoutes);
app.use('/api/users', userRoutes);

// Root endpoint
app.get('/', (req: Request, res: Response) => {
  res.send('TradeSpotter Backend running...');
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`[server] listening on http://localhost:${port}`);
});
