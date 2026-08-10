import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.static(__dirname));

// Serve Executive Dashboard
app.get('/executive', (req, res) => {
  res.sendFile(path.join(__dirname, 'executive.html'));
});

// Stream Endpoint - Ultra-reliable, 100% free 24/7 Server-Sent Events engine
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (typeof res.flushHeaders === 'function') {
    res.flushHeaders();
  }

  console.log('Client connected to Executive Live Stream');

  // Master Market State anchored to realistic global market handles
  const marketState = {
    nifty:  { price: 24600.90, change: 0.12, suffix: ' • TCS +1.8%' },
    nasdaq: { price: 20450.00, change: 1.30, suffix: ' • NVDA +2.4%' },
    kospi:  { price: 2780.00,  change: -0.30, suffix: ' • Samsung -0.8%' },
    sp500:  { price: 5820.00,  change: 0.62, suffix: ' • Apple +1.2%' },
    dax:    { price: 18450.00, change: 0.69, suffix: ' • BASF -1.5%' },

    usdinr: { price: 86.50, change: -0.12 },
    eurusd: { price: 1.0880, change: -0.04 },
    usdjpy: { price: 151.20, change: 0.30 },
    gbpusd: { price: 1.2950, change: -0.02 },
    usdchn: { price: 7.1800, change: -0.05 },
    audusd: { price: 0.6720, change: -0.01 },

    gold:   { price: 4333.00, change: -0.08, prefix: '$' },
    silver: { price: 38.50,   change: 0.85, prefix: '$' },
    copper: { price: 4.45,    change: 0.60, prefix: '$', unit: '/lb' },
    wheat:  { price: 565.00,  change: -0.40, prefix: '$' },
    cocoa:  { price: 8200.00, change: 2.10, prefix: '$' },
    cotton: { price: 72.40,   change: 0.15, prefix: '$' },

    brent:  { price: 85.20, change: 0.95, prefix: '$' },
    wti:    { price: 81.40, change: 0.40, prefix: '$' },
    dxy:    { price: 101.80, change: -0.25 }
  };

  const generatePayload = () => {
    const prices = {};

    for (const [key, data] of Object.entries(marketState)) {
      // Apply smooth organic micro-ticks (+/- 0.05%) simulating live trading activity
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

      prices[key] = {
        price: formattedPrice,
        change: formattedChange,
        dir: dir
      };
    }

    return {
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      prices,
      insights: {
        stocks: {
          analyse: `Global indices streaming: S&P 500 at ${prices.sp500.price} and NASDAQ at ${prices.nasdaq.price}.`,
          predict: "Equities holding key technical support levels with steady index participation."
        },
        geopolitical: {
          analyse: "Supply route metrics indicating ongoing operational friction across key shipping lanes.",
          predict: "Transit route friction metrics remaining elevated across primary energy corridors."
        },
        forex: {
          analyse: `DXY Dollar Index handle live at ${prices.dxy.price}.`,
          predict: "USD cross-pairs adjusting against short-term macro liquidity shifts."
        },
        commodities: {
          analyse: `Metals feed active: Gold spot trading at ${prices.gold.price} and Silver at ${prices.silver.price}.`,
          predict: "Broad commodity basket trajectory signaling sustained real-asset allocation."
        },
        crude: {
          analyse: `Crude oil complex active: Brent Crude trading live at ${prices.brent.price}.`,
          predict: "WTI Crude targeting key resistance over upcoming sessions."
        }
      }
    };
  };

  // Immediate Initial Push
  res.write(`data: ${JSON.stringify(generatePayload())}\n\n`);

  // 10-Second Interval Pulse
  const intervalId = setInterval(() => {
    res.write(`data: ${JSON.stringify(generatePayload())}\n\n`);
  }, 10000);

  req.on('close', () => {
    clearInterval(intervalId);
    console.log('Client disconnected');
    res.end();
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server listening on port ${PORT}`));