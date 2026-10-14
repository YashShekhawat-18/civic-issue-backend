# Civic Issue Reporter - Frontend

Next.js (App Router) + Tailwind CSS frontend for the Civic Issue Reporting and Management System.
The backend (FastAPI + MongoDB) lives in a separate repository.

## Run it

1. Start the backend (default http://localhost:8000).
2. In this folder:
   ```
   npm install
   copy .env.local.example .env.local      (Windows)   |   cp .env.local.example .env.local   (Mac/Linux)
   npm run dev
   ```
3. Open http://localhost:3000

The backend's `CLIENT_URL` in its `.env` must be `http://localhost:3000` (CORS).

## Scripts
- `npm run dev` - development server
- `npm run build` / `npm start` - production build and run
- `npm run lint` - ESLint
- `npm test` - unit tests (Vitest)

## Structure
- `lib/api.js` - one `fetch` wrapper: adds the Bearer token, unwraps `{success,message,data}`, throws `ApiError`
- `lib/validation.js` - form checks mirroring backend rules
- `context/AuthContext.jsx` - login / register / logout, restores the session from the stored token
- `components/RoleGuard.jsx` - only lets listed roles into a section (backend still enforces roles)
- `app/citizen`, `app/worker`, `app/admin` - one area per role

## Security notes
- The token is kept in `localStorage`. Simple, but readable by any script on the page (XSS). httpOnly cookies are safer but need backend changes.
- Never commit `.env.local`.
