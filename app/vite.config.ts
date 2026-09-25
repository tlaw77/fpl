import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
});
