# NFL DFS Live Standings - Frontend

React + TypeScript frontend for the NFL DFS Live Standings platform.

## Features

- 📡 **Real-time WebSocket Updates** - Live contest updates via WebSocket
- 🎮 **Updater Control Panel** - Start/stop background automation
- 📊 **Live Standings Table** - View all contests and their current state
- 🔔 **Push Notifications** - Real-time update notifications
- 📈 **Pre-game vs Live Comparison** - See how scores change during games
- 🎨 **Modern UI** - Built with Tailwind CSS and Lucide icons

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Fast development server
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Beautiful icons
- **Recharts** - Data visualization

## Installation

```bash
# Install dependencies
cd frontend
npm install
```

## Development

### Start the Development Server

```bash
npm run dev
```

This will start the frontend on **http://localhost:3000**

### Make Sure Backend is Running

The frontend requires the backend to be running on port 8000:

```bash
# In another terminal
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── UpdaterControl.tsx      # Control panel for background updater
│   │   ├── ContestList.tsx         # List of all contests
│   │   ├── WebSocketStatus.tsx     # WebSocket connection indicator
│   │   └── UpdateNotification.tsx  # Toast notifications
│   ├── services/            # API and WebSocket services
│   │   ├── api.ts                  # HTTP API client
│   │   └── websocket.ts            # WebSocket client
│   ├── hooks/               # Custom React hooks
│   │   └── useWebSocket.ts         # WebSocket hook
│   ├── types/               # TypeScript types
│   │   └── index.ts                # Type definitions
│   ├── App.tsx              # Main application component
│   ├── main.tsx             # Application entry point
│   └── index.css            # Global styles
├── package.json
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── tsconfig.json            # TypeScript configuration
```

## Features Walkthrough

### 1. WebSocket Connection

The frontend automatically connects to the backend WebSocket endpoint (`ws://localhost:8000/ws`) on load. Connection status is shown in the top-right corner.

### 2. Updater Control

- **Start Updater** - Begins automatic updates every 2 minutes
- **Stop Updater** - Stops background updates
- **Trigger Now** - Manually trigger an immediate update

### 3. Contest List

Displays all monitored contests with:
- Contest ID and metadata
- Number of lineups
- Entry fee
- Slate type (Main/Showdown)
- Pre-game vs live average scores
- Update count
- Active/inactive status
- Last update timestamp

### 4. Real-time Updates

When contests are updated (either automatically or manually), you'll see:
- Toast notification in the top-right
- Updated contest data in the list
- Change indicators showing score improvements/declines

## API Integration

The frontend communicates with the backend via:

### HTTP REST API

```typescript
// Health check
GET /health

// Contests
GET /api/contests
GET /api/contests/{id}
POST /api/contests/{id}/deactivate
DELETE /api/contests/{id}

// Updater control
GET /api/updater/status
POST /api/updater/control
POST /api/updater/trigger
```

### WebSocket

```typescript
// Connect
ws://localhost:8000/ws

// Receive messages
{
  type: 'contest_update',
  contest_id: 'demo_123',
  timestamp: '2025-10-06T12:34:56',
  data: { ... }
}
```

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

To preview the production build:

```bash
npm run preview
```

## Environment Variables

No environment variables required for local development. The frontend assumes:
- Backend API: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws`

These can be configured in `vite.config.ts` if needed.

## Troubleshooting

### Cannot connect to backend

**Error:** "Cannot connect to backend server"

**Solution:** Make sure the backend is running:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

### WebSocket disconnected

**Error:** WebSocket status shows "Disconnected"

**Solution:**
1. Check backend is running
2. Refresh the page
3. Check browser console for WebSocket errors

### No contests showing

**Info:** "No contests are being monitored"

**Solution:** Load contest data using demo scripts:
```bash
cd backend
python examples/demo_automation.py
```

## Development Tips

### Hot Module Replacement

Vite provides instant HMR. Changes to React components appear immediately without full page reload.

### TypeScript

All types are defined in `src/types/index.ts`. The project uses strict TypeScript mode.

### Tailwind CSS

Use Tailwind utility classes for styling. Custom styles go in `src/index.css`.

### Icons

Icons from `lucide-react`:
```tsx
import { Play, Stop, RefreshCw } from 'lucide-react';
```

## Future Enhancements (Phase 5)

- File upload for Stokastic/DK CSVs
- Detailed lineup breakdown modal
- Player performance drill-down
- Charts and visualizations with Recharts
- Historical data and trends
- Contest comparison view
- Export results to CSV

## License

MIT License - See [LICENSE](../LICENSE) for details
