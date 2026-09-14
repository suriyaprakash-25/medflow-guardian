import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const appSource = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const viteSource = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8');

test('admin routes are loaded through React.lazy behind Suspense', () => {
  assert.match(appSource, /lazy\(\(\) => import\('\.\/pages\/Dashboard'\)\)/);
  assert.match(appSource, /lazy\(\(\) => import\('\.\/pages\/Organizations'\)\)/);
  assert.match(appSource, /<Suspense\s+fallback=/);
});

test('admin build isolates heavy vendor families', () => {
  assert.match(viteSource, /manualChunks:\s*vendorChunk/);
  assert.match(viteSource, /charts-vendor/);
  assert.match(viteSource, /react-vendor/);
  assert.match(viteSource, /icons-vendor/);
});
