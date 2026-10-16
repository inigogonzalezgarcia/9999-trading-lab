import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the API runs on :8000; set VITE_API_BASE to point elsewhere.
// In the production image the UI is served by FastAPI itself, so the base is empty (same origin).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: { outDir: 'dist', sourcemap: false },
});
