# Tradespotter Server (Express + TypeScript)

A simple Express server written in TypeScript to support the Tradespotter frontend.

## Prerequisites
- Node.js v18+ (v20 recommended)
- npm

## Setup
```bash
# Install dependencies
npm install

# Start in development (auto-restart)
npm run dev

# Build for production
npm run build

# Start built server
npm start
```

The server listens on `PORT` (default 4000). Copy `.env.example` to `.env` to customize.

## Endpoints
- `GET /api/health` → `{ "status": "ok" }`
