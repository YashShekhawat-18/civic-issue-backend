// Single place that knows where the backend lives.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");

// Uploaded photos are served by the backend at /uploads/... (outside /api/v1).
export const FILES_URL = API_URL.replace(/\/api\/v1$/, "");

export const TOKEN_KEY = "civic_access_token";
