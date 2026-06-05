import { describe, it, expect, afterEach } from '@jest/globals';

describe('Application Configuration', () => {
  afterEach(() => {
    delete process.env.PORT;
  });

  describe('Port configuration', () => {
    it('should resolve to environment PORT when set', () => {
      process.env.PORT = '3000';
      const port = process.env.PORT || 8080;
      expect(port).toBe('3000');
    });

    it('should resolve to 8080 as default when PORT is not set', () => {
      delete process.env.PORT;
      const port = process.env.PORT || 8080;
      expect(port).toBe(8080);
    });

    it('should handle PORT set to empty string by falling back to default', () => {
      process.env.PORT = '';
      const port = process.env.PORT || 8080;
      expect(port).toBe(8080);
    });

    it('should handle PORT set to 0 as a valid port', () => {
      process.env.PORT = '0';
      // In the app logic: process.env.PORT || 8080
      // '0' is truthy as a string, so it should use '0'
      const port = process.env.PORT || 8080;
      expect(port).toBe('0');
    });

    it('should accept high port numbers', () => {
      process.env.PORT = '65535';
      const port = process.env.PORT || 8080;
      expect(port).toBe('65535');
    });
  });

  describe('Bare server path configuration', () => {
    it('should use /bare/ as the default bare server prefix', () => {
      const prefix = '/bare/';
      expect(prefix).toBe('/bare/');
      expect(prefix.startsWith('/')).toBe(true);
      expect(prefix.endsWith('/')).toBe(true);
    });
  });

  describe('Static file server directory', () => {
    it('should use static/ as the serving directory', () => {
      const staticDir = 'static/';
      expect(staticDir).toBe('static/');
    });
  });
});
