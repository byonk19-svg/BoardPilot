import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./tests',use:{baseURL:process.env.WOODWORK_TEST_URL || 'http://127.0.0.1:5173',headless:true},workers:1,reporter:'list'});
