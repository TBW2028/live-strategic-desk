const express = require('express');
const cors = require('cors');

const app = express();

// Enable CORS so your frontend can connect without cross-origin blocks
app.use(cors({ origin: '*' }));

// SSE Stream Endpoint
app.get('/stream', (req, res) => {
  // Required Server-Sent Events headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders(); // Send headers immediately

  console.log('Client connected to SSE stream');

  // Send an initial handshake message so the browser knows it connected
  const welcomeMsg = {
    id: "SYS-000",
    severity: "high",
    category: "SYSTEM STREAM",
    headline: "Live Connection Established with Render Backend",
    punchline: "Server-Sent Events active and streaming live data.",
    geo: "📍 Render Edge Node",
    timeStr: "JUST NOW",
    assetsImpact: [{ name: "API Health", dir: "OPTIMAL", cls: "direction-up" }],
    sectorImpact: [{ name: "Data Ingestion", dir: "ACTIVE", cls: "direction-up" }],
    macroImpact: [{ name: "Network Latency", dir: "MINIMAL", cls: "direction-up" }],
    sources: 1
  };

  res.write(`data: ${JSON.stringify(welcomeMsg)}\n\n`);

  // Stream new live headlines every 10 seconds
  const intervalId = setInterval(() => {
    const newsItem = {
      id: "HND-" + Math.floor(100 + Math.random() * 900),
      severity: "urgent",
      category: "MARKET INTELLIGENCE",
      headline: "Automated Signal Update Transmitted from Render",
      punchline: "Real-time SSE event received across active strategic connections.",
      geo: "📍 Global Feed",
      timeStr: "JUST NOW",
      assetsImpact: [
        { name: "Spot Liquidity Index", dir: "SURGING", cls: "direction-up" },
        { name: "Volatile Forex Pairs", dir: "MIXED", cls: "direction-mixed" }
      ],
      sectorImpact: [
        { name: "Fintech Streaming Infrastructure", dir: "OPTIMAL", cls: "direction-up" }
      ],
      macroImpact: [
        { name: "Real-Time Data Velocity", dir: "ACCELERATING", cls: "direction-up" }
      ],
      sources: 4
    };

    res.write(`data: ${JSON.stringify(newsItem)}\n\n`);
  }, 10000);

  // Clean up timer when connection closes
  req.on('close', () => {
    clearInterval(intervalId);
    console.log('Client disconnected');
    res.end();
  });
});

// Port binding for Render
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});