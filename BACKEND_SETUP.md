# Backend Architecture Setup

This document describes the new backend architecture that separates frontend from direct database access.

## Architecture Overview

```
Frontend (React) → Backend API (Express) → Supabase Database
```

**Benefits:**
- Centralized business logic
- Better security (service role key only on server)
- Easier to add caching, rate limiting, etc.
- Single source of truth for data access

## What Changed

### Before
Frontend directly called Supabase:
```typescript
const { data } = await supabase.from('politicians').select('*')
```

### After
Frontend calls backend API:
```typescript
const data = await getAllPoliticians()
```

Backend handles Supabase:
```typescript
// In politicianService.ts
const { data } = await supabase.from('politicians').select('*')
```

## File Structure

### Backend (`/server`)
```
server/
├── src/
│   ├── config/
│   │   └── supabase.ts              # Supabase client
│   ├── controllers/
│   │   └── politicianController.ts  # HTTP request handlers
│   ├── interfaces/
│   │   ├── Politician.ts            # Type definitions
│   │   └── Trade.ts
│   ├── routes/
│   │   └── politicianRoutes.ts      # Route definitions
│   ├── services/
│   │   └── politicianService.ts     # Database logic
│   └── index.ts                     # Server entry & Express setup
└── .env                             # Server environment variables
```

### Frontend (`/src`)
```
src/
├── api/
│   └── politicians.ts               # API client functions
└── pages/
    └── Index.tsx                    # Updated to use API
```

## Setup Instructions

### 1. Install Backend Dependencies

```bash
cd server
npm install
```

All dependencies including `@supabase/supabase-js` and `express-rate-limit` are already configured in `package.json`.

### 2. Configure Backend Environment

Create `server/.env`:
```bash
PORT=4000
FRONTEND_URL=https://your-production-frontend.com
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

**Important:** Use the **service role key**, not the anon key, for server-side operations.

### 3. Configure Frontend Environment

Create `.env` in project root:
```bash
VITE_API_URL=http://localhost:4000/api
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
```

### 4. Start Backend Server

```bash
cd server
npm run dev
```

Server runs on `http://localhost:4000`

### 5. Start Frontend

```bash
npm run dev
```

Frontend runs on `http://localhost:5173` (or your configured port)

## API Endpoints

### Politicians

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/politicians` | Get all politicians |
| GET | `/api/politicians/:id` | Get politician by ID |
| GET | `/api/politicians/trades?limit=20` | Get recent trades |

### Response Format

All endpoints return:
```typescript
{
  success: boolean;
  data?: T;
  error?: string;
}
```

## Migration Status

### ✅ Migrated to Backend
- Get all politicians
- Get recent trades
- Get user follows
- Follow/unfollow politicians

### 🔄 Still Using Direct Supabase (Frontend)
- User authentication (handled by Supabase Auth)

## Features

### Security & Performance
- **Rate Limiting**: 100 requests per minute per IP
- **CORS Protection**: Whitelist-based origin validation
- **Request Logging**: Automatic logging with timestamps and duration
- **Body Size Limits**: 10MB max for JSON/URL-encoded payloads

### Allowed Origins (Development)
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (React default)
- `http://localhost:8080`
- `http://localhost:8081`
- Custom production URL via `FRONTEND_URL` env var

## Next Steps

1. **Set up environment variables** in both frontend and backend
2. **Test the endpoints**: Start both servers and verify data loads
3. **Migrate remaining endpoints**: User follows, alerts, etc.
4. **Add authentication middleware** for protected routes

## Troubleshooting

### Backend won't start
- Check `.env` file exists in `/server`
- Verify Supabase credentials are correct
- Ensure port 4000 is not in use

### Frontend can't connect to backend
- Verify backend is running on port 4000
- Check `VITE_API_URL` in frontend `.env`
- Check browser console for CORS errors

### No data returned
- Verify Supabase service role key has proper permissions
- Check backend logs for errors
- Test Supabase connection directly

## Architecture Patterns

### Service Layer
Business logic and database queries:
```typescript
export class PoliticianService {
  async getAllPoliticians(): Promise<Politician[]> {
    const { data, error } = await supabase.from('politicians').select('*')
    if (error) throw new Error(error.message)
    return data || []
  }
}
```

### Controller Layer
HTTP request/response handling:
export class PoliticianController {
  async getAllPoliticians(req: Request, res: Response): Promise<void> {
    try {
      const politicians = await politicianService.getAllPoliticians()
      res.json({
        success: true,
        data: politicians.map(politician => ({
          id: politician.id,
          full_name: politician.full_name,
          state: politician.state,
          chamber: politician.chamber,
        })),
      })
    } catch (error) {
      res.status(500).json({ success: false, error: error.message })
    }
  }
}

### Frontend API Client
Type-safe API calls:
```typescript
export async function getAllPoliticians(): Promise<Politician[]> {
  const response = await fetch(`${API_BASE_URL}/politicians`)
  const result = await response.json()
  return result.data
}
```

This architecture makes it easy to add features like caching, rate limiting, authentication middleware, and more complex business logic without touching the frontend.
