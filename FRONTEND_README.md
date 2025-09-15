# Tradespotter Frontend

React + TypeScript + Vite frontend application for tracking congressional trading activity.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [Building & Deployment](#building--deployment)
- [Features](#features)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Tradespotter frontend is a modern React application that provides:

- **Congressional Trade Tracking** - View and analyze trades by congress members
- **Real-time Data** - Connected to Supabase for live updates
- **Modern UI** - Built with shadcn/ui components and Tailwind CSS
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Type Safety** - Full TypeScript implementation
- **Fast Development** - Vite for instant hot module replacement

## 📋 Prerequisites

### Required Software
- **Node.js v18+** (v20 recommended)
- **npm** (comes with Node.js)

### System Requirements
- **RAM**: 1GB minimum for development
- **Disk**: 500MB for dependencies
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# From the root directory
npm install
```

### Step 2: Configure Environment

```bash
# Copy environment template (if it exists)
cp .env.example .env

# Or create .env file with Supabase config:
echo "VITE_SUPABASE_URL=your-supabase-url" > .env
echo "VITE_SUPABASE_ANON_KEY=your-supabase-anon-key" >> .env
```

### Step 3: Start Development Server

```bash
npm run dev
```

The application will start at `http://localhost:5173`

### Step 4: Verify Setup

Open your browser to `http://localhost:5173` and you should see the Tradespotter application.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Supabase Configuration (Required)
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Optional Configuration
VITE_APP_TITLE=Tradespotter
VITE_API_BASE_URL=http://localhost:4000
```

**How to get Supabase credentials:**
1. Go to your Supabase project dashboard
2. Click **Settings** → **API**
3. Copy the **URL** and **anon/public** key (NOT the service role key)

### Available Settings

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | ✅ | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anonymous/public key |
| `VITE_APP_TITLE` | ❌ | Application title (default: "Tradespotter") |
| `VITE_API_BASE_URL` | ❌ | Backend API URL (if using separate server) |

## 📁 Project Structure

```
src/
├── components/
│   ├── ui/                     # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── ...
│   ├── CongressMemberCard.tsx  # Member display component
│   └── TradeCard.tsx          # Trade display component
├── hooks/
│   ├── use-mobile.tsx         # Mobile detection hook
│   ├── use-toast.ts           # Toast notifications
│   └── useAuth.tsx            # Authentication hook
├── integrations/
│   └── supabase/              # Supabase client and types
│       ├── client.ts
│       └── types.ts
├── lib/
│   └── utils.ts               # Utility functions
├── pages/                     # Page components (if using routing)
├── App.tsx                    # Main application component
├── main.tsx                   # Application entry point
└── index.css                  # Global styles
```

## 🔧 Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Build for development (with source maps)
npm run build:dev

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Key Technologies

- **React 18** - UI library with hooks and concurrent features
- **TypeScript** - Type safety and better developer experience
- **Vite** - Fast build tool and development server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality React components
- **Supabase** - Backend-as-a-Service for database and auth
- **React Query** - Data fetching and caching
- **React Router** - Client-side routing
- **Recharts** - Data visualization components

### Development Workflow

1. **Start Development**: `npm run dev`
2. **Make Changes**: Edit files in `src/`
3. **Hot Reload**: Changes appear instantly in browser
4. **Type Check**: TypeScript errors show in terminal and IDE
5. **Lint**: Run `npm run lint` to check code quality

### Adding New Components

```bash
# Using shadcn/ui CLI (if installed)
npx shadcn-ui@latest add button

# Or manually create in src/components/
# Follow existing patterns for consistency
```

### Styling Guidelines

- Use Tailwind CSS classes for styling
- Follow shadcn/ui patterns for component structure
- Use CSS variables for theme colors
- Responsive design with mobile-first approach

## 🏗️ Building & Deployment

### Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview
```

### Static Hosting

The built application is static and can be deployed to:

- **Vercel** (recommended)
- **Netlify**
- **GitHub Pages**
- **AWS S3 + CloudFront**
- **Any static hosting service**

### Vercel Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Or connect GitHub repo for automatic deployments
```

### Netlify Deployment

```bash
# Build command: npm run build
# Publish directory: dist
```

### Environment Variables in Production

Set these in your hosting platform:

```bash
VITE_SUPABASE_URL=your-production-supabase-url
VITE_SUPABASE_ANON_KEY=your-production-anon-key
```

## 🎨 Features

### Current Features

- **Trade Visualization** - View congressional trades in cards/tables
- **Member Profiles** - Information about congress members
- **Responsive Design** - Works on all device sizes
- **Dark/Light Theme** - Theme switching support
- **Type Safety** - Full TypeScript coverage

### Planned Features

- **User Authentication** - Login/signup with Supabase Auth
- **Trade Alerts** - Notifications for followed members
- **Advanced Filtering** - Filter by date, amount, asset type
- **Data Export** - Export trade data to CSV/Excel
- **Charts & Analytics** - Visual analysis of trading patterns

## 🔍 Troubleshooting

### Common Issues

**Build Errors**
```bash
npm run lint
npm run build
```
Fix TypeScript and linting errors shown in output.

**Environment Variables Not Working**
- Ensure variables start with `VITE_`
- Restart development server after changing `.env`
- Check variables are properly set in production

**Supabase Connection Issues**
```bash
# Check network tab in browser dev tools
# Verify VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
# Ensure Supabase project is active
```

**Styling Issues**
```bash
# Ensure Tailwind CSS is working
# Check if components are imported correctly
# Verify CSS classes are valid
```

### Development Tips

1. **Hot Reload Issues**: Restart `npm run dev`
2. **TypeScript Errors**: Check terminal and IDE for errors
3. **Component Issues**: Verify imports and props
4. **Styling Problems**: Use browser dev tools to inspect

### Performance Optimization

```bash
# Analyze bundle size
npm run build
npx vite-bundle-analyzer dist

# Optimize images and assets
# Use React.lazy() for code splitting
# Implement proper loading states
```

## 🔗 Integration

### Backend Integration

Connect to your Express server:

```typescript
// In src/lib/api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000';

export const fetchTrades = async () => {
  const response = await fetch(`${API_BASE_URL}/api/trades`);
  return response.json();
};
```

### Supabase Integration

```typescript
// In src/integrations/supabase/client.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
```

### Authentication Setup

```typescript
// In src/hooks/useAuth.tsx
import { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  return { user };
};
```

## 📝 Next Steps

1. **Set up Authentication** - Implement user login/signup
2. **Add Real Data** - Connect to your trades database
3. **Implement Filtering** - Add search and filter capabilities
4. **Add Charts** - Visualize trading data with Recharts
5. **Mobile Optimization** - Enhance mobile experience
6. **Testing** - Add unit and integration tests
7. **Performance** - Optimize bundle size and loading

The frontend is ready for development and can be easily extended with additional features as your application grows.
