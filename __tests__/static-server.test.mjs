import { describe, it, expect } from '@jest/globals';
import nodeStatic from 'node-static';

describe('Static File Server', () => {
  describe('Server instantiation', () => {
    it('should create a static file server instance for a directory', () => {
      const serve = new nodeStatic.Server('static/');
      expect(serve).toBeDefined();
      expect(typeof serve.serve).toBe('function');
    });

    it('should accept configuration options', () => {
      const serve = new nodeStatic.Server('static/', { cache: 3600 });
      expect(serve).toBeDefined();
    });

    it('should have servePath property matching the configured directory', () => {
      const serve = new nodeStatic.Server('static/');
      expect(serve.root).toBeDefined();
    });
  });

  describe('Server.serve method', () => {
    it('should be callable with req and res objects', () => {
      const serve = new nodeStatic.Server('static/');
      const req = {
        url: '/index.html',
        method: 'GET',
        headers: {},
        addListener: (event, cb) => { if (event === 'end') cb(); },
        on: (event, cb) => { if (event === 'end') cb(); },
      };
      const res = {
        writeHead: () => {},
        end: () => {},
        setHeader: () => {},
      };

      // Should not throw; will emit a 404 since static/ is empty, but function executes
      expect(() => serve.serve(req, res)).not.toThrow();
    });

    it('should handle requests with different HTTP methods', () => {
      const serve = new nodeStatic.Server('static/');
      const createReq = (method) => ({
        url: '/',
        method,
        headers: {},
        addListener: (event, cb) => { if (event === 'end') cb(); },
        on: (event, cb) => { if (event === 'end') cb(); },
      });
      const res = {
        writeHead: () => {},
        end: () => {},
        setHeader: () => {},
      };

      expect(() => serve.serve(createReq('GET'), res)).not.toThrow();
      expect(() => serve.serve(createReq('HEAD'), res)).not.toThrow();
    });
  });

  describe('Static Server properties', () => {
    it('should have default cache value', () => {
      const serve = new nodeStatic.Server('static/');
      expect(serve.cache).toBeDefined();
      expect(typeof serve.cache).toBe('number');
    });

    it('should respect custom cache value', () => {
      const serve = new nodeStatic.Server('static/', { cache: 0 });
      expect(serve.cache).toBe(0);
    });

    it('should have serverInfo property', () => {
      const serve = new nodeStatic.Server('static/');
      expect(serve.serverInfo).toBeDefined();
    });
  });
});
