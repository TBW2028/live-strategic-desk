import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.static(__dirname));

// Serve Climate & Natural Calamity Observatory at Root and /climate
app.get(['/', '/climate'], (req, res) => {
  res.sendFile(path.join(__dirname, 'climate.html'));
});

// Optional: Live telemetry SSE stream endpoint for real-time background pulses if needed
app.get('/api/climate-stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (typeof res.flushHeaders === 'function') {
    res.flushHeaders();
  }

  const sendPulse = () => {
    const payload = {
      timestamp: new Date().toLocaleTimeString(),
      status: "Telemetry Active",
    };
    res.write(`data: ${JSON.stringify(payload)}\n\n`);
  };

  sendPulse();
  const intervalId = setInterval(sendPulse, 15000);

  req.on('close', () => {
    clearInterval(intervalId);
    res.end();
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Climate Observatory Server online on port ${PORT}`));