import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.static(__dirname));

// Serve Dashboard at both root and /executive route
app.get(['/', '/executive'], (req, res) => {
  res.sendFile(path.join(__dirname, 'executive.html'));
});

// SSE Streaming Telemetry Endpoint
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (typeof res.flushHeaders === 'function') {
    res.flushHeaders();
  }

  console.log('Client connected to Executive Strategic Desk Stream');

  const marketState = {
    bitcoin: { price: 68450.00, change: 2.45, prefix: '$' },
    gold:    { price: 2415.50,  change: 0.85, prefix: '$' },
    silver:  { price: 31.50,    change: 1.45, prefix: '$' },
    nasdaq:  { price: 20450.00, change: 0.95, suffix: ' • NVDA +2.4%' },
    sp500:   { price: 5820.00,  change: 0.55, suffix: ' • Apple +1.2%' },
    nifty:   { price: 24850.00, change: 0.65, suffix: ' • TCS +1.8%' },
    dax:     { price: 18450.00, change: -0.80, suffix: ' • BASF -1.5%' },
    kospi:   { price: 2780.00,  change: -0.30, suffix: ' • Samsung -0.8%' },
    copper:  { price: 4.45,     change: 0.60, prefix: '$', unit: '/lb' },
    brent:   { price: 85.20,    change: 0.95, prefix: '$' },
    wti:     { price: 81.40,    change: 0.80, prefix: '$' },
    dxy:     { price: 101.80,   change: -0.25 },
    usdinr:  { price: 86.50,    change: 0.10 },
    eurusd:  { price: 1.0880,   change: 0.15 },
    usdjpy:  { price: 151.20,   change: -0.45 },
    gbpusd:  { price: 1.2950,   change: 0.28 }
  };

  const generatePayload = () => {
    const prices = {};

    for (const [key, data] of Object.entries(marketState)) {
      const jitter = (Math.random() - 0.49) * 0.001;
      data.price = Number((data.price * (1 + jitter)).toFixed(data.price < 10 ? 4 : 2));

      const dir = data.change >= 0 ? 'up' : 'down';
      const sign = data.change >= 0 ? '+' : '';

      let formattedPrice = data.price >= 1000 
        ? data.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) 
        : data.price.toFixed(data.price < 10 ? 4 : 2);

      if (data.prefix) formattedPrice = `${data.prefix}${formattedPrice}`;
      if (data.unit) formattedPrice = `${formattedPrice}${data.unit}`;

      let formattedChange = `${sign}${data.change.toFixed(2)}%`;
      if (data.suffix) formattedChange = `${formattedChange}${data.suffix}`;

      prices[key] = { price: formattedPrice, change: formattedChange, dir };
    }

    return {
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      prices,
      insights: [
        {
          title: "The Quantum Horizon of Energy Independence",
          body: "Direct solar-to-hydrogen photoreactor panels and laser fusion funding milestones are bypassing traditional electrolysis barriers, reducing reliance on conventional electrical infrastructure."
        },
        {
          title: "Industrial Retooling Amidst Regional Pressures",
          body: "Major chemical and manufacturing conglomerates are executing multi-year transformation programs to reduce net-cash fixed costs by 20% to combat regional margin compression."
        },
        {
          title: "Critical Mineral Supply Chain Resilience",
          body: "Innovations in soda pressure leaching processes are enabling single-pass, high-purity lithium extraction while suppressing soluble impurities for next-generation energy storage."
        }
      ]
    };
  };

  res.write(`data: ${JSON.stringify(generatePayload())}\n\n`);

  const intervalId = setInterval(() => {
    res.write(`data: ${JSON.stringify(generatePayload())}\n\n`);
  }, 10000);

  req.on('close', () => {
    clearInterval(intervalId);
    res.end();
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Executive Strategic Desk online on port ${PORT}`));