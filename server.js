import express from 'express';
import Parser from 'rss-parser';
import { GoogleGenAI } from '@google/genai';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());

const parser = new Parser();
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

// SSE Clients Registry
let clients = [];
const seenHeadlines = new Set();

// 1. Server-Sent Events Endpoint
app.get('/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  clients.push(res);

  req.on('close', () => {
    clients = clients.filter(client => client !== res);
  });
});

// Broadcast payload to all connected frontends
function broadcast(data) {
  clients.forEach(client => {
    client.write(`data: ${JSON.stringify(data)}\n\n`);
  });
}

// 2. Fetch Latest Headlines from Live News Sources
async function fetchLatestNews() {
  const feeds = [
    'https://feeds.a.dj.com/rss/RSSWorldNews.xml', // Wall Street Journal
    'https://search.cnbc.com/rs/search/combinednews.rss?partnerId=wrntw&id=10000664' // CNBC Top News
  ];

  for (const feedUrl of feeds) {
    try {
      const feed = await parser.parseURL(feedUrl);
      for (const item of feed.items.slice(0, 3)) {
        if (!seenHeadlines.has(item.title)) {
          seenHeadlines.add(item.title);
          return { headline: item.title, snippet: item.contentSnippet || item.title, link: item.link };
        }
      }
    } catch (err) {
      console.error(`Error fetching feed ${feedUrl}:`, err.message);
    }
  }
  return null;
}

// 3. PhD Financial Analyst Prompt with Active Model Endpoints
async function analyzeWithAI(newsItem) {
  const prompt = `
  You are an elite Wall Street Macro Strategist & PhD Economist. Analyze this headline:
  Headline: "${newsItem.headline}"
  Summary: "${newsItem.snippet}"

  Output strictly in valid JSON format matching this schema:
  {
    "category": "MACRO / CATEGORY",
    "severity": "urgent",
    "headline": "${newsItem.headline}",
    "punchline": "Concise 1-sentence strategic summary",
    "geo": "📍 Location",
    "assetsImpact": [
      { "name": "Asset / Currency name", "dir": "POSITIVE", "cls": "direction-up" }
    ],
    "sectorImpact": [
      { "name": "Sector / Industry name", "dir": "NEGATIVE", "cls": "direction-down" }
    ],
    "macroImpact": [
      { "name": "Livelihood / Economic reality", "dir": "MIXED", "cls": "direction-mixed" }
    ]
  }
  Provide 2-3 specific items for each impact array. Response MUST be strict JSON only, no markdown ticks.
  `;

  // Models in priority order
  const modelsToTry = [
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite'
  ];

  for (const modelName of modelsToTry) {
    try {
      console.log(`🤖 Requesting analysis from model: ${modelName}`);
      const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt,
      });

      const cleanJson = response.text.replace(/```json|```/g, '').trim();
      return JSON.parse(cleanJson);
    } catch (err) {
      console.warn(`⚠️ Model ${modelName} call missed, trying fallback...`);
    }
  }

  console.error('❌ All Gemini model endpoints failed.');
  return null;
}

// 4. Main 1-Minute Engine Execution Loop
async function runEngine() {
  console.log('⚡ Engine checking sources...');
  const freshNews = await fetchLatestNews();

  if (freshNews) {
    console.log(`[NEW EVENT DETECTED]: ${freshNews.headline}`);
    const analysis = await analyzeWithAI(freshNews);

    if (analysis) {
      analysis.id = `HND-${Math.floor(100 + Math.random() * 900)}`;
      analysis.timeStr = 'JUST NOW';
      analysis.sources = Math.floor(Math.random() * 5) + 3;
      
      console.log('📡 Broadcasting live analysis to web desk...');
      broadcast(analysis);
    }
  } else {
    console.log('No new breaking headlines found in this 60s cycle.');
  }
}

// Run engine every 60 seconds (60,000 ms)
setInterval(runEngine, 60000);
runEngine(); // Trigger immediately on start

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`🚀 Live Strategic Engine active on port ${PORT}`));