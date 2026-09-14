import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const appRoot = new URL('../', import.meta.url);
const read = (path) => readFileSync(new URL(path, appRoot), 'utf8');

test('API client keeps access tokens memory-only and refresh-cookie backed', () => {
  const source = read('src/lib/api.ts');

  assert.match(source, /export function getAccessToken\(\)/);
  assert.match(source, /export function setAccessToken\(token: string\)/);
  assert.match(source, /export function clearAccessToken\(\)/);
  assert.match(source, /export async function ensureSession\(\)/);
  assert.match(source, /\/api\/auth\/refresh/);
  assert.match(source, /withCredentials: true/);
  assert.match(source, /originalRemoveItem\.call\(window\.localStorage, 'token'\)/);
  assert.doesNotMatch(source, /localStorage\.setItem\(\s*['"]token['"]/);
});

test('API client uses same-origin fallback so Vite can proxy local admin requests', () => {
  const source = read('src/lib/api.ts');
  const viteConfig = read('vite.config.ts');

  assert.match(source, /const API_BASE_URL = import\.meta\.env\.VITE_API_BASE_URL \|\| '';/);
  assert.doesNotMatch(source, /localhost:8000/);
  assert.match(viteConfig, /'\/api'/);
  assert.match(viteConfig, /localhost:8080/);
});

test('protected routes bootstrap authenticated state through ensureSession', () => {
  const source = read('src/App.tsx');

  assert.match(source, /ensureSession/);
  assert.match(source, /authorized === null/);
  assert.match(source, /Navigate to="\/login"/);
});

test('admin portal consumes shared API contracts', () => {
  const source = read('src/pages/Login.tsx');
  assert.match(source, /@shared\/api\/contracts/);
  assert.match(source, /AuthUserContract/);
  assert.match(source, /LoginResponseContract/);
});
