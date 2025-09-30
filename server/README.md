# Tradespotter Server

Express.js + TypeScript backend server for the Tradespotter congressional trading application.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Tradespotter server is a lightweight Express.js backend that provides:

- RESTful API endpoints for the frontend
- Health check monitoring
- CORS support for cross-origin requests
- TypeScript for type safety
- Development hot-reloading

## 📋 Prerequisites

### Required Software
- **Node.js v18+** (v20 recommended)
- **npm** (comes with Node.js)

### System Requirements
- **RAM**: 512MB minimum
- **Disk**: 100MB for dependencies
- **Network**: Internet connection for package installation

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd server
npm install
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your Supabase credentials
# PORT=4000
# SUPABASE_URL=your_supabase_url
# SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Step 3: Start Development Server

```bash
# Start with hot-reloading
npm run dev
```

The server will start at `http://localhost:4000`

### Step 4: Verify Setup

Open your browser or use curl:

```bash
curl http://localhost:4000/api/health
# Should return: {"status":"ok"}
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the server directory:

```bash
# Server Configuration
PORT=4000                    # Port to run the server on

# Frontend URL (for CORS in production)
FRONTEND_URL=https://your-production-frontend.com

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Available Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `4000` | Port number for the server |
| `FRONTEND_URL` | - | Production frontend URL (for CORS) |
| `SUPABASE_URL` | - | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | - | Supabase service role key (for server-side operations) |

## 🔌 API Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "ok"
}
```

**Purpose:** Verify server is running and responsive

### Politicians

#### Get All Politicians
```http
GET /api/politicians
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "full_name": "John Doe",
      "party": "Democrat",
      "state": "CA",
      "chamber": "House",
      ...
    }
  ]
}
```

#### Get Politician by ID
```http
GET /api/politicians/:id
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "full_name": "John Doe",
    ...
  }
}
```

#### Get Recent Trades
```http
GET /api/politicians/trades?limit=20
```

**Query Parameters:**
- `limit` (optional): Number of trades to return (default: 20)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "asset_name": "Apple Inc.",
      "ticker": "AAPL",
      "transaction_date": "2025-01-15",
      "politicians": {
        "id": "uuid",
        "full_name": "John Doe",
        "party": "Democrat",
        "state": "CA",
        "chamber": "House"
      },
      ...
    }
  ]
}
```

## 🔧 Development

### Available Scripts

```bash
# Development (with hot-reload)
npm run dev

# Type checking
npm run typecheck

# Build for production
npm run build

# Start production build
npm start
```

### Project Structure

```
server/
├── src/
│   ├── config/
│   │   └── supabase.ts     # Supabase client configuration
│   ├── controllers/
│   │   └── politicianController.ts  # Request/response handlers
│   ├── interfaces/
│   │   ├── Politician.ts   # Politician type definitions
│   │   └── Trade.ts        # Trade type definitions
│   ├── routes/
│   │   └── politicianRoutes.ts      # API route definitions
│   ├── services/
│   │   └── politicianService.ts     # Business logic & DB queries
│   └── index.ts            # Server entry point & Express config
├── dist/                   # Built JavaScript (after npm run build)
├── package.json            # Dependencies and scripts
├── tsconfig.json          # TypeScript configuration
├── .env.example           # Environment template
└── README.md              # This file
```

### Adding New Features

1. **Add Routes**: Create route files in `src/routes/` and register in `src/index.ts`
2. **Add Middleware**: Configure in `src/index.ts`
3. **Environment Config**: Add to `.env` and load in `src/index.ts`
4. **Type Definitions**: Create interface files in `src/interfaces/`

### Code Style

The project uses TypeScript with strict type checking:

```typescript
// Example route with proper typing
app.get('/api/example', (req: express.Request, res: express.Response) => {
  res.json({ message: 'Hello World' });
});
```

## 🚀 Production Deployment

### Build for Production

```bash
# Install dependencies
npm ci --only=production

# Build TypeScript
npm run build

# Start production server
npm start
```

### Environment Setup

```bash
# Production environment variables
NODE_ENV=production
PORT=4000
```

### Process Management

Use PM2 for production process management:

```bash
# Install PM2 globally
npm install -g pm2

# Start with PM2
pm2 start dist/index.js --name "tradespotter-server"

# Monitor
pm2 status
pm2 logs tradespotter-server
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 4000

CMD ["npm", "start"]
```

Build and run:

```bash
docker build -t tradespotter-server .
docker run -p 4000:4000 tradespotter-server
```

## 🔍 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
Error: listen EADDRINUSE: address already in use :::4000
```
Solution: Change PORT in `.env` or kill the process using port 4000

**TypeScript Errors**
```bash
npm run typecheck
```
Solution: Fix type errors shown in output

**Module Not Found**
```bash
npm install
```
Solution: Reinstall dependencies

### Development Tips

1. **Hot Reload Not Working**: Restart `npm run dev`
2. **CORS Issues**: Configure CORS origin in `src/app.ts`
3. **Environment Variables**: Restart server after changing `.env`

### Logs and Debugging

```bash
# View development logs
npm run dev

# Check production logs with PM2
pm2 logs tradespotter-server

# Enable debug mode
DEBUG=* npm run dev
```

### Health Check Failures

If health check fails:

1. Verify server is running: `curl http://localhost:4000/api/health`
2. Check port configuration in `.env`
3. Ensure no firewall blocking the port
4. Review server logs for errors

## 🔗 Integration

### Frontend Integration

The server is designed to work with the Tradespotter React frontend:

```javascript
// Frontend API call example
const response = await fetch('http://localhost:4000/api/health');
const data = await response.json();
```

### Database Integration

To add database connectivity:

```bash
# Install database client (example: Supabase)
npm install @supabase/supabase-js

# Add to src/app.ts
import { createClient } from '@supabase/supabase-js'
```

### External APIs

Add API integrations as needed:

```typescript
// Example: Add to src/app.ts
app.get('/api/external-data', async (req, res) => {
  try {
    const data = await fetchExternalAPI();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch data' });
  }
});
```

## 📝 Next Steps

1. **Add Database Integration**: Connect to Supabase for data persistence
2. **Add Authentication**: Implement user authentication middleware
3. **Add API Routes**: Create endpoints for trades, members, alerts
4. **Add Validation**: Implement request validation middleware
5. **Add Testing**: Set up Jest for unit and integration tests

The server is ready for development and can be easily extended with additional features as your application grows.
