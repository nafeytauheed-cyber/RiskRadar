import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', retries: 0, use: {baseURL:'http://localhost:5173', screenshot:'only-on-failure'},
  webServer: {command:'npm run dev -- --host 127.0.0.1',url:'http://localhost:5173',reuseExistingServer:false},
});
