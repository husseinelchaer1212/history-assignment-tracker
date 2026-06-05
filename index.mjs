import createServer from '@tomphttp/bare-server-node';
import http from 'http';
import https from 'https';
import { readFileSync, existsSync } from 'fs';
import serveStatic from 'serve-static';
import finalhandler from 'finalhandler';

const bare = createServer('/bare/');
const serve = serveStatic('static/', { dotfiles: 'deny' });

function requestHandler(req, res) {
	res.setHeader('X-Content-Type-Options', 'nosniff');
	res.setHeader('X-Frame-Options', 'SAMEORIGIN');
	res.setHeader('Referrer-Policy', 'no-referrer');

	if (bare.shouldRoute(req)) {
		bare.routeRequest(req, res);
	} else {
		serve(req, res, finalhandler(req, res));
	}
}

function upgradeHandler(req, socket, head) {
	if (bare.shouldRoute(req, socket, head)) {
		bare.routeUpgrade(req, socket, head);
	} else {
		socket.end();
	}
}

const sslKeyPath = process.env.SSL_KEY;
const sslCertPath = process.env.SSL_CERT;
let server;

if (sslKeyPath && sslCertPath && existsSync(sslKeyPath) && existsSync(sslCertPath)) {
	server = https.createServer(
		{ key: readFileSync(sslKeyPath), cert: readFileSync(sslCertPath) },
		requestHandler
	);
} else {
	server = http.createServer(requestHandler);
}

server.on('upgrade', upgradeHandler);

server.listen({
	port: process.env.PORT || 8080,
});
