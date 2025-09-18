# Hospital Management System - Claude Instructions

## Project Overview
- Hospital management system with React frontend and streaming backend
- Door tracker concept: BLE-enabled devices (tabs/displays/watches) for room tracking
- Frontend on port 3000, backend on port 8001

## Coding Standards
- **Database:** All lowercase column names (patientid, firstname, createdat)
- **Backend API:** Transforms database lowercase → camelCase for frontend
- **Frontend:** CamelCase for all data (patientId, firstName, createdAt)
- NO snake_case anywhere in the codebase
- Match enumerators to existing frontend patterns
- Check existing files before creating new ones
- Prefer editing existing files over creating new ones
- Security focus between frontend and backend
- MISRA-C or ISO medical and HIPAA compliant code

## Database Architecture
- **PostgreSQL:** Main data storage (all lowercase columns)
- **TimescaleDB:** Time-series vitals data (all lowercase columns)
- Backend transforms database responses from lowercase to camelCase for frontend consumption

## Hardware Integration
- ESP32 watches send patient data over WiFi or BLE to displays
- Displays forward data to backend
- Real-time vital signs monitoring

## Architecture Notes
- Frontend: React TypeScript app in `hospital-display-app/`
- Backend: Streaming backend in `hospital-backend/`
- Plan to convert React frontend to Android app
- **Bed Assignment**: Room and bed numbers are **manual entries** by nursing staff during admission processing

## Development Workflow
- Always run linting and type checking after code changes
- Use ports 3000 and 8001 only
- Consider CORS requirements for security
- also indian medical and other laws primaritly. hipaa is secondary.
- no incomplete stubs, we want a full production ready end to end backend for patinets. from recommending admission to approving and removing watch when being discharged. we will do tye best possible clinical trcacking and automation for patinets and caregivers