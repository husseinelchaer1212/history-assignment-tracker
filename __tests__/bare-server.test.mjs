import { describe, it, expect } from '@jest/globals';
import createServer from '@tomphttp/bare-server-node';

describe('Bare Server Integration', () => {
  let bare;

  it('should create a bare server instance with /bare/ prefix', () => {
    bare = createServer('/bare/');
    expect(bare).toBeDefined();
    expect(typeof bare.shouldRoute).toBe('function');
    expect(typeof bare.routeRequest).toBe('function');
    expect(typeof bare.routeUpgrade).toBe('function');
  });

  it('shouldRoute should return true for requests to /bare/ path', () => {
    bare = createServer('/bare/');
    const req = { url: '/bare/v1/', headers: { host: 'localhost:8080' } };
    const result = bare.shouldRoute(req);
    expect(result).toBe(true);
  });

  it('shouldRoute should return false for requests outside /bare/ path', () => {
    bare = createServer('/bare/');
    const req = { url: '/index.html', headers: { host: 'localhost:8080' } };
    const result = bare.shouldRoute(req);
    expect(result).toBe(false);
  });

  it('shouldRoute should return false for root path', () => {
    bare = createServer('/bare/');
    const req = { url: '/', headers: { host: 'localhost:8080' } };
    const result = bare.shouldRoute(req);
    expect(result).toBe(false);
  });

  it('shouldRoute should return true for nested bare paths', () => {
    bare = createServer('/bare/');
    const req = { url: '/bare/some/nested/path', headers: { host: 'localhost:8080' } };
    const result = bare.shouldRoute(req);
    expect(result).toBe(true);
  });

  it('should handle different prefix configurations', () => {
    const customBare = createServer('/api/');
    const req = { url: '/api/test', headers: { host: 'localhost:8080' } };
    expect(customBare.shouldRoute(req)).toBe(true);

    const req2 = { url: '/bare/test', headers: { host: 'localhost:8080' } };
    expect(customBare.shouldRoute(req2)).toBe(false);
  });
});
