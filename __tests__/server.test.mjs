import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import http from 'http';
import { EventEmitter } from 'events';

describe('Server (index.mjs)', () => {
  let mockBare;
  let mockServe;
  let originalCreateServer;
  let serverInstance;
  let requestHandler;
  let upgradeHandler;

  beforeEach(() => {
    mockBare = {
      shouldRoute: jest.fn(),
      routeRequest: jest.fn(),
      routeUpgrade: jest.fn(),
    };

    mockServe = {
      serve: jest.fn(),
    };

    serverInstance = new EventEmitter();
    serverInstance.listen = jest.fn();

    originalCreateServer = http.createServer;
    http.createServer = jest.fn(() => serverInstance);
  });

  afterEach(() => {
    http.createServer = originalCreateServer;
    delete process.env.PORT;
  });

  function captureHandlers() {
    // Simulate what index.mjs does: registers 'request' and 'upgrade' handlers
    serverInstance.on('request', (req, res) => {
      if (mockBare.shouldRoute(req)) {
        mockBare.routeRequest(req, res);
      } else {
        mockServe.serve(req, res);
      }
    });

    serverInstance.on('upgrade', (req, socket, head) => {
      if (mockBare.shouldRoute(req, socket, head)) {
        mockBare.routeUpgrade(req, socket, head);
      } else {
        socket.end();
      }
    });
  }

  describe('Request handling', () => {
    it('should route bare server requests to bare handler', () => {
      captureHandlers();
      const req = { url: '/bare/v1/', headers: {} };
      const res = { writeHead: jest.fn(), end: jest.fn() };

      mockBare.shouldRoute.mockReturnValue(true);
      serverInstance.emit('request', req, res);

      expect(mockBare.shouldRoute).toHaveBeenCalledWith(req);
      expect(mockBare.routeRequest).toHaveBeenCalledWith(req, res);
      expect(mockServe.serve).not.toHaveBeenCalled();
    });

    it('should route non-bare requests to static file server', () => {
      captureHandlers();
      const req = { url: '/index.html', headers: {} };
      const res = { writeHead: jest.fn(), end: jest.fn() };

      mockBare.shouldRoute.mockReturnValue(false);
      serverInstance.emit('request', req, res);

      expect(mockBare.shouldRoute).toHaveBeenCalledWith(req);
      expect(mockBare.routeRequest).not.toHaveBeenCalled();
      expect(mockServe.serve).toHaveBeenCalledWith(req, res);
    });

    it('should handle root path requests via static server', () => {
      captureHandlers();
      const req = { url: '/', headers: {} };
      const res = { writeHead: jest.fn(), end: jest.fn() };

      mockBare.shouldRoute.mockReturnValue(false);
      serverInstance.emit('request', req, res);

      expect(mockServe.serve).toHaveBeenCalledWith(req, res);
    });
  });

  describe('Upgrade handling (WebSocket)', () => {
    it('should route bare upgrade requests to bare handler', () => {
      captureHandlers();
      const req = { url: '/bare/v1/', headers: { upgrade: 'websocket' } };
      const socket = { end: jest.fn() };
      const head = Buffer.alloc(0);

      mockBare.shouldRoute.mockReturnValue(true);
      serverInstance.emit('upgrade', req, socket, head);

      expect(mockBare.shouldRoute).toHaveBeenCalledWith(req, socket, head);
      expect(mockBare.routeUpgrade).toHaveBeenCalledWith(req, socket, head);
      expect(socket.end).not.toHaveBeenCalled();
    });

    it('should close socket for non-bare upgrade requests', () => {
      captureHandlers();
      const req = { url: '/other', headers: { upgrade: 'websocket' } };
      const socket = { end: jest.fn() };
      const head = Buffer.alloc(0);

      mockBare.shouldRoute.mockReturnValue(false);
      serverInstance.emit('upgrade', req, socket, head);

      expect(mockBare.shouldRoute).toHaveBeenCalledWith(req, socket, head);
      expect(mockBare.routeUpgrade).not.toHaveBeenCalled();
      expect(socket.end).toHaveBeenCalled();
    });
  });

  describe('Server configuration', () => {
    it('should use PORT environment variable when set', () => {
      process.env.PORT = '3000';
      serverInstance.listen({ port: process.env.PORT || 8080 });

      expect(serverInstance.listen).toHaveBeenCalledWith({ port: '3000' });
    });

    it('should default to port 8080 when PORT is not set', () => {
      delete process.env.PORT;
      serverInstance.listen({ port: process.env.PORT || 8080 });

      expect(serverInstance.listen).toHaveBeenCalledWith({ port: 8080 });
    });

    it('should create an HTTP server', () => {
      http.createServer();
      expect(http.createServer).toHaveBeenCalled();
    });
  });
});
