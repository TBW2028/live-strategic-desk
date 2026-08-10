import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.static(__dirname));

// Route for serving executive dashboard
app.get('/executive', (req, res) => {
  res.sendFile(path.join(__dirname, 'executive.html'));
});

// FIXED: Endpoint changed from '/stream' to '/api/stream' to match executive.html
app.get('/api/stream', (req, res) => {
  // Essential headers for Server-Sent Events (SSE) and Render reverse proxies
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (typeof res.flushHeaders === 'function') {
    res.flushHeaders();
  }

  console.log('Client connected to Executive SSE stream');

  // Payload structure matching the frontend updateUI expectations
  const buildPayload = () => ({
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    insights: {
      stocks: {
        analyse: "Tech sector momentum surging following strong semiconductor wafer yields in Taiwan.",
        predict: "S&P 500 and NASDAQ 100 expected to sustain short-term bullish continuation."
      },
      geopolitical: {
        analyse: "OPEC+ output cuts generating immediate pricing pressures across global refined fuel lines.",
        predict: "Transit route friction metrics remaining elevated across primary energy corridors."
      },
      forex: {
        analyse: "DXY index adjusting lower as market digests potential Federal Reserve policy pauses.",
        predict: "USD/JPY exposure subject to short-term carry unwind following BOJ curve adjustments."
      },
      commodities: {
        analyse: "Gold and precious metals finding solid institutional support near $2,415/oz levels.",
        predict: "Broad commodity basket trajectory signaling sustained real-asset allocation."
      },
      crude: {
        analyse: "Brent Crude trading higher (+4.2%) reacting to sudden Middle East production restrictions.",
        predict: "WTI Crude targeting $82.50 key resistance over the upcoming trading sessions."
      }
    }
  });

  // 1. Send initial handshake payload immediately so EventSource connects instantly
  res.write(`data: ${JSON.stringify(buildPayload())}\n\n`);

  // 2. Stream dynamic updates every 8 seconds
  const intervalId = setInterval(() => {
    res.write(`data: ${JSON.stringify(buildPayload())}\n\n`);
  }, 8000);

  req.on('close', () => {
    clearInterval(intervalId);
    console.log('Client disconnected from SSE stream');
    res.end();
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});