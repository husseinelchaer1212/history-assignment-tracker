import createServer from '@tomphttp/bare-server-node';
import http from 'http';
import nodeStatic from 'node-static';

const bare = createServer('/bare/');
const serve = new nodeStatic.Server('static/');

const server = http.createServer();

server.on('request', (req, res) => {
	if (bare.shouldRoute(req)) {
		try {
			bare.routeRequest(req, res);
		} catch (err) {
			console.error('Bare server request error:', err);
			if (!res.headersSent) {
				res.writeHead(500, { 'Content-Type': 'text/plain' });
				res.end('Internal Server Error');
			}
		}
	} else {
		serve.serve(req, res, (err) => {
			if (err) {
				console.error('Static file error:', err.message, req.url);
				res.writeHead(err.status || 500, { 'Content-Type': 'text/plain' });
				res.end(err.status === 404 ? 'Not Found' : 'Internal Server Error');
			}
		});
	}
});

server.on('upgrade', (req, socket, head) => {
	if (bare.shouldRoute(req)) {
		try {
			bare.routeUpgrade(req, socket, head);
		} catch (err) {
			console.error('Bare server upgrade error:', err);
			socket.end();
		}
	} else {
		console.warn('Rejected non-bare upgrade request:', req.url);
		socket.end();
	}
});

server.on('error', (err) => {
	console.error('Server error:', err);
	process.exit(1);
});

const port = process.env.PORT || 8080;
server.listen({ port }, () => {
	console.log(`Server listening on port ${port}`);
});

process.on('uncaughtException', (err) => {
	console.error('Uncaught exception:', err);
	process.exit(1);
});

process.on('unhandledRejection', (reason) => {
	console.error('Unhandled rejection:', reason);
	process.exit(1);
});
