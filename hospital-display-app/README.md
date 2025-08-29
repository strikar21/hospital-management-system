# Hospital Display App

A React-based hospital patient monitoring system with real-time vital signs tracking, alerts, and comprehensive patient management.

## Features

- **Patient Dashboard**: Real-time monitoring of multiple patients
- **Vital Signs Tracking**: Heart rate, blood pressure, temperature, oxygen saturation, ECG/EEG
- **Alert System**: Critical condition notifications with severity levels
- **NFC Authentication**: Quick staff login via NFC cards
- **Room Proximity**: Automatic patient detection based on location
- **Bedside Mode**: Focused single-patient monitoring
- **Case Sheet Management**: Complete patient records and medication tracking

## Backend Integration

This app connects to the Hospital IoT Backend (FastAPI) located in the `../hospital-backend` directory. The backend provides:

- RESTful API endpoints for patient data
- WebSocket connections for real-time updates
- Authentication and authorization
- IoT device integration (500+ devices)
- MQTT messaging for sensor data

## Quick Start

### Option 1: Run Frontend and Backend Together (Recommended)

```bash
# Install dependencies
npm install

# Start both frontend and backend
npm run dev
```

This will start:
- Backend (FastAPI) on http://localhost:8001
- Frontend (React) on http://localhost:3000

### Option 2: Run Components Separately

```bash
# Terminal 1 - Start backend
cd ../hospital-backend
python run_dev.py

# Terminal 2 - Start frontend
npm start
```

## Available Scripts

### `npm start`

Runs the React app in development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### `npm run dev` or `npm run start:full`

Starts both the backend and frontend simultaneously using concurrently.

### `npm run start:backend`

Starts only the backend FastAPI server.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Backend configuration
REACT_APP_BACKEND_URL=http://localhost:8001
REACT_APP_WS_URL=ws://localhost:8001

# Set to 'true' to use real backend, 'false' to use mock data
REACT_APP_USE_BACKEND=true

# Development settings
REACT_APP_ENV=development
```

### Mock Data vs Backend

- **Backend Mode**: Set `REACT_APP_USE_BACKEND=true` - Uses real FastAPI backend
- **Mock Mode**: Set `REACT_APP_USE_BACKEND=false` - Uses hardcoded mock data for testing

## Authentication

### Demo Credentials

**Staff ID Format**: 4-digit numbers (0001-9999)

- **Doctor**: `0001` / `hospital123` (or PIN-based)
- **Nurse**: `0002` / `hospital123` (or PIN-based) 
- **Admin**: `9999` / `hospital123`

**Examples**: 0001, 0123, 5678, 9999

### NFC Authentication

The app supports NFC card authentication. Demo NFC IDs are available in the system.

## Architecture

```
hospital-display-app/          # React frontend
├── src/
│   ├── api.ts                # Backend integration & mock data
│   ├── types.ts              # TypeScript type definitions
│   ├── App.tsx               # Main application component
│   ├── Dashboard.tsx         # Patient monitoring dashboard
│   ├── PatientDetail.tsx     # Individual patient details
│   └── ...
├── .env                      # Environment configuration
└── package.json

../hospital-backend/           # FastAPI backend
├── app/
│   ├── api/v1/              # REST API endpoints
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   └── main.py              # FastAPI application
└── run_dev.py               # Development server
```

## API Integration

The frontend integrates with these backend endpoints:

- `POST /api/v1/auth/login` - Staff authentication
- `GET /api/v1/mobile/patients` - Patient data
- `GET /api/v1/vitals/{patient_id}` - Vital signs
- `WS /ws/patient/{patient_id}` - Real-time updates
- `POST /api/v1/alerts/acknowledge` - Alert management

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/)
- [Create React App Documentation](https://facebook.github.io/create-react-app/docs/getting-started)
