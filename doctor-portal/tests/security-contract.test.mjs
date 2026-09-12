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

test('protected routes bootstrap authenticated state through ensureSession', () => {
  const source = read('src/App.tsx');

  assert.match(source, /ensureSession/);
  assert.match(source, /authorized === null/);
  assert.match(source, /Navigate to="\/login"/);
});
