const { createProxyMiddleware } = require('http-proxy-middleware');
const https = require('https');

// Create a custom HTTPS agent with minimal SSL settings for development
const httpsAgent = new https.Agent({
  rejectUnauthorized: false,
  checkServerIdentity: () => undefined,
  secureProtocol: 'TLS_method',
});

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'https://localhost:8001',
      changeOrigin: true,
      secure: false,
      agent: httpsAgent,
      logLevel: 'debug',
      headers: {
        'Connection': 'keep-alive',
      },
      onError: (err, req, res) => {
        console.error('Proxy error:', err);
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log('Proxying request:', req.method, req.url);
      }
    })
  );
  
  app.use(
    '/ws',
    createProxyMiddleware({
      target: 'wss://localhost:8001',
      changeOrigin: true,
      secure: false,
      ws: true,
      logLevel: 'debug',
      onError: (err, req, res) => {
        console.error('WebSocket proxy error:', err);
      }
    })
  );
};