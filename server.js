import express from 'express';
import cors from 'cors';

const app = express();

app.use(cors({ origin: '*' }));

// Real-world scenario template generator
const strategicScenarios = [
  {
    category: "GEOPOLITICAL & TRADE",
    headline: "OPEC+ Announces Unplanned Production Cut of 1.2M Barrels/Day",
    punchline: "Brent crude jumps 4.2% in Asian trading; supply concerns ripple through refined fuel futures.",
    geo: "📍 Riyadh, Saudi Arabia",
    assetsImpact: [{ name: "Brent Crude Futures", dir: "📈 +4.2%", cls: "direction-up" }, { name: "WTI Crude", dir: "📈 +3.8%", cls: "direction-up" }],
    sectorImpact: [{ name: "Energy & Exploration", dir: "BULLISH", cls: "direction-up" }, { name: "Aviation & Logistics", dir: "MARGIN PRESSURE", cls: "direction-down" }],
    macroImpact: [{ name: "Global Headline Inflation", dir: "+0.15% EST", cls: "direction-up" }],
    sources: 6
  },
  {
    category: "MONETARY POLICY",
    headline: "Federal Reserve Signals Rate Pause Amid Cooling Core PCE Data",
    punchline: "Yields on 10-Year Treasury notes ease 8bps; tech sector rallies during early trading hours.",
    geo: "📍 Washington, D.C.",
    assetsImpact: [{ name: "US 10Y Yield", dir: "📉 4.12% (-8bps)", cls: "direction-down" }, { name: "S&P 500 Futures", dir: "📈 +0.8%", cls: "direction-up" }],
    sectorImpact: [{ name: "SaaS & Cloud Software", dir: "INFLOWS", cls: "direction-up" }, { name: "Commercial Banking", dir: "NET INTEREST COMPRESSION", cls: "direction-down" }],
    macroImpact: [{ name: "Dollar Index (DXY)", dir: "📉 103.4 (-0.45%)", cls: "direction-down" }],
    sources: 8
  },
  {
    category: "CHIP ARCHITECTURE & TECH",
    headline: "Next-Gen 2nm Wafer Yields Exceed 75% at Leading Taiwan Fab",
    punchline: "Commercial production timeline accelerated by 2 quarters; advanced AI silicon supply bottleneck eases.",
    geo: "📍 Hsinchu, Taiwan",
    assetsImpact: [{ name: "Semiconductor ETF (SMH)", dir: "📈 +2.9%", cls: "direction-up" }, { name: "Foundry CapEx Index", dir: "SURGING", cls: "direction-up" }],
    sectorImpact: [{ name: "Hyperscale Cloud Hardware", dir: "COST ACCELERATION", cls: "direction-down" }, { name: "AI Compute Integrators", dir: "OPTIMAL", cls: "direction-up" }],
    macroImpact: [{ name: "Tech CapEx Output", dir: "$140B PROJECTED", cls: "direction-up" }],
    sources: 5
  },
  {
    category: "GLOBAL SUPPLY CHAIN",
    headline: "Critical Bottleneck Resolved at Panama Canal as Draft Limits Increase",
    punchline: "Daily vessel transit count raised from 24 to 36; Atlantic-to-Pacific container spot rates drop 12%.",
    geo: "📍 Panama City, Panama",
    assetsImpact: [{ name: "Container Freight Rate Index", dir: "📉 -12.4%", cls: "direction-down" }, { name: "Dry Bulk Shipping", dir: "NORMALIZING", cls: "direction-up" }],
    sectorImpact: [{ name: "Retail Imports", dir: "MARGIN BENEFIT", cls: "direction-up" }, { name: "Air Cargo Chartering", dir: "DEMAND ESIING", cls: "direction-down" }],
    macroImpact: [{ name: "Supply Chain Volatility Index", dir: "LOWEST IN 18M", cls: "direction-up" }],
    sources: 4
  },
  {
    category: "CURRENCY & FOREX",
    headline: "Bank of Japan Adjusts Yield Curve Band; Yen Rallies 150 Pips Against USD",
    punchline: "Carry trade unwind triggers cross-market rebalancing across Asian equity indexes.",
    geo: "📍 Tokyo, Japan",
    assetsImpact: [{ name: "USD/JPY", dir: "📉 148.20 (-1.1%)", cls: "direction-down" }, { name: "Nikkei 225 Futures", dir: "📉 -1.4%", cls: "direction-down" }],
    sectorImpact: [{ name: "Japanese Automotive Exporters", dir: "HEADWIND", cls: "direction-down" }, { name: "Domestic Japanese Financials", dir: "OUTPERFORMING", cls: "direction-up" }],
    macroImpact: [{ name: "Global Liquidity Spread", dir: "TIGHTENING", cls: "direction-down" }],
    sources: 7
  }
];

app.get('/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  if (typeof res.flushHeaders === 'function') {
    res.flushHeaders();
  }

  console.log('Client connected to SSE stream');

  // Initial welcome message
  const welcomeMsg = {
    id: "SYS-INIT-" + Date.now(),
    severity: "high",
    category: "SYSTEM MONITOR",
    headline: "Live Executive Intelligence Stream Established",
    punchline: "Connected to real-time strategic signal engine. Updates arriving on shift intervals.",
    geo: "📍 Global Feed",
    timeStr: "JUST NOW",
    assetsImpact: [{ name: "Stream Engine Status", dir: "ONLINE", cls: "direction-up" }],
    sectorImpact: [{ name: "Latency", dir: "< 15ms", cls: "direction-up" }],
    macroImpact: [{ name: "Data Pipeline Integrity", dir: "VERIFIED", cls: "direction-up" }],
    sources: 12
  };

  res.write(`data: ${JSON.stringify(welcomeMsg)}\n\n`);

  let index = 0;
  // Stream dynamic headline items every 8 seconds
  const intervalId = setInterval(() => {
    const template = strategicScenarios[index % strategicScenarios.length];
    
    // Inject dynamic variations and unique IDs to prevent duplicates
    const newsItem = {
      ...template,
      id: "SIG-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
      timeStr: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };

    res.write(`data: ${JSON.stringify(newsItem)}\n\n`);
    index++;
  }, 8000);

  req.on('close', () => {
    clearInterval(intervalId);
    console.log('Client disconnected');
    res.end();
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});