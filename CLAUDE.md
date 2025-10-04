# Hospital Management System - Claude Instructions

## Development Approach - TOP PRIORITY REQUIREMENTS

### MANDATORY BEHAVIOR CHECK - CLAUDE MUST DO BEFORE EVERY ACTION:
1. **Research first** - Check what actual data exists using tools
2. **Ask clarifying questions** - If uncertain about anything, ask before proceeding
3. **Document plan** - Make a file and refer to it before executing
4. **NEVER assume or guess data/IDs** - If Claude uses made-up data like "PAT0001", STOP immediately and research actual data first

### Core Requirements:
- **NEVER assume stuff** - always ask relevant questions first
- **Ask before making changes** - get user approval before implementing solutions
- **When user asks to show/list something** - make a file and show the content
- **Before making any change**, understand the bug by examining ALL related files
- **Code must be modular and small** - break down large functions into smaller, focused components
- Always analyze the full context before proposing solutions
- Ask clarifying questions about requirements, expected behavior, and edge cases
- Examine existing patterns in the codebase before implementing new features
- Investigate thoroughly before suggesting changes

## Project Overview
- Hospital management system with React frontend and streaming backend
- Door tracker concept: BLE-enabled devices (tabs/displays/watches) for room tracking
- Frontend on port 3000, backend on port 8001

## Coding Standards
- **Database:** All camelCase column names (patientId, firstName, createdAt)
- **Backend API:** All camelCase data handling (patientId, firstName, createdAt)
- **Frontend:** All camelCase data handling (patientId, firstName, createdAt)
- **STRICT CAMELCASE ONLY:** No snake_case, no lowercase, no PascalCase, no kebab-case
- **CONSISTENT CAMELCASE:** All variables, properties, and data fields must be camelCase
- Match enumerators to existing frontend patterns
- Check existing files before creating new ones
- Prefer editing existing files over creating new ones
- Security focus between frontend and backend
- MISRA-C or ISO medical and HIPAA compliant code

## Database Architecture
- **PostgreSQL:** Main data storage (all camelCase columns)
- **TimescaleDB:** Time-series vitals data (all camelCase columns)
- Backend maintains camelCase data throughout - consistent with frontend

## Hardware Integration
- ESP32 watches send patient data over WiFi or BLE to displays
- Displays forward data to backend
- Real-time vital signs monitoring

## Alert and Analysis System
- **ALL alerts are generated on BACKEND only** - no frontend alert generation
- **ALL arrhythmia detection happens on BACKEND** - frontend only displays backend results
- **ALL clinical logic is in BACKEND** - frontend is just a display skin/UI layer
- **ALL medical calculations, validations, and business logic on BACKEND**
- **ALERTS: Watch OR Backend generates alerts** - frontend just displays them
- **NO FRONTEND ALERT PROCESSING** - frontend receives and displays alerts only
- Frontend is display-only for medical alerts and analysis
- Backend handles all medical calculations, risk assessments, and alert triggers
- Frontend just renders data received from backend - no medical processing
- Alert sources: ESP32 watches → backend OR backend analysis → frontend display

## Architecture Notes
- Frontend: React TypeScript app in `hospital-display-app/`
- Backend: Streaming backend in `hospital-backend/`
- Plan to convert React frontend to Android app
- **Bed Assignment**: Room and bed numbers are **manual entries** by nursing staff during admission processing

## Regulatory Compliance - INDIA FOCUSED
- **PRIMARY**: Indian medical and healthcare laws and regulations
- **SECONDARY**: HIPAA and similar international privacy standards for reference
- **NO FDA REQUIREMENTS** - This is for India deployment, not US
- Focus on Indian Medical Council (IMC) guidelines
- Comply with Digital Personal Data Protection Act (DPDP) 2023
- Follow Clinical Establishments Act requirements
- Adhere to Drugs and Cosmetics Act for medication handling

## Development Workflow
- Always run linting and type checking after code changes
- Use ports 3000 and 8001 only
- Consider CORS requirements for security
- Indian medical and other laws primarily. HIPAA is secondary for reference only.
- no incomplete stubs, we want a full production ready end to end backend for patinets. from recommending admission to approving and removing watch when being discharged. we will do tye best possible clinical trcacking and automation for patinets and caregivers