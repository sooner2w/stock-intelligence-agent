# Stock Intelligence Agent

> Built the research stack hedge funds pay $25,000/year for — using free public data, a hand-written AI agent loop, and Python.

**[Live Case Study →](https://breon.ai)** &nbsp;|&nbsp; Built by [Brandon Breon](https://breon.ai)

---

## What This Is

A full-stack AI stock research tool with three integrated layers:

1. **AI Agent** — Claude-powered with a manual tool-calling loop (no LangChain, no AutoGen), three-layer persistent memory, and 11 live tools
2. **Research Dashboard** — real-time fundamentals, SEC insider trades, options flow, and unusual activity — all in one screen
3. **Conviction Scoring** — a 0–10 score that stacks 7 independent signals to remove guesswork from options unusual activity

---

## The Core Idea

Retail investors see one signal at a time. Institutions stack them.

This tool does the stacking automatically:

- ⚡ Unusual options activity detected
- Cross-referenced against insider buying (SEC EDGAR)
- Cross-referenced against fundamentals (PEG, growth, margins)
- Cross-referenced against momentum (vs 50-day MA)
- Cross-referenced against analyst consensus

Result: a single conviction score with a plain-English recommendation.

---

## Features

### Research Mode (single stock)
- Live price, 3-month chart, 50d MA, analyst target overlay
- Full fundamentals: P/E, forward P/E, PEG, revenue growth, margins, ROE, free cash flow, debt/equity
- 5-signal summary bar: valuation · growth · analyst · momentum · short interest
- **SEC EDGAR insider trades** — parsed from raw Form 4 XML filings — with buy/sell ratio
- Recent news with links

### Options Flow
- Full call/put chain for any expiration date
- Put/call ratio (bullish/bearish interpretation)
- **Max pain** calculation — where most options expire worthless
- **IV smile chart** — implied volatility across strikes
- **Open interest by strike** — where the big positions are sitting
- **⚡ Unusual activity detection** — volume ≥ 3× open interest = fresh money
- **Conviction score (0–10)** on every flagged contract

### Discover Mode (no ticker needed)
- Scores 80+ stocks across 7 sectors automatically
- Filters: sector, minimum score, analyst rating, momentum, PEG
- Top 3 picks surfaced as cards with upside %, score, and analyst rating

### AI Agent (terminal)
Ask in plain English. The agent decides which tools to use and in what order:

```
You: Search for AI infrastructure stocks, pull data on the top 3 mentioned,
     compare them, and write a report to ~/Desktop/ai_stocks.md

Agent: [web_search] → [get_stock_data x3] → [compare_stocks] → [write_file]
       Done. Report written to Desktop.
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Claude Opus 4.7                   │
│              (reasoning + tool orchestration)        │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   Short-Term      Long-Term      Semantic
   Memory          Memory         Memory
   (sliding        (SQLite —      (ChromaDB +
    window)         all turns,     sentence-
                    resumable)     transformers)
                       │
         ┌─────────────┼──────────────────┐
         ▼             ▼                  ▼
   Yahoo Finance   SEC EDGAR          DuckDuckGo
   (price, options, (Form 4 insider   (web search)
    fundamentals)   trades — XML)
```

**The loop** (written by hand — no framework abstractions):
```
user message
    → save to short-term + long-term memory
    → search semantic memory for relevant context
    → call Claude with tools list
    → if tool_use: execute tool, feed result back, loop
    → if end_turn: save response, return to user
```

---

## Stack

| Layer | Technology | Why |
|---|---|---|
| AI | Claude Opus 4.7 (Anthropic) | Best reasoning + adaptive thinking |
| Vector memory | ChromaDB + sentence-transformers | Local, free, semantic search |
| Episodic memory | SQLite | Zero setup, survives restarts |
| Stock data | yfinance | Free, full fundamentals + options |
| Insider data | SEC EDGAR API | Free, official, 48hr lag |
| Web search | DuckDuckGo API | No key needed |
| Dashboard | Streamlit + Plotly | Fast to ship, professional output |

**Monthly cost: $0** outside Claude API usage.

---

## Setup

```bash
git clone https://github.com/brandonbreon/stock-intelligence-agent
cd stock-intelligence-agent

pip install -r requirements.txt

cp .env.example .env
# Add your Anthropic API key to .env

# Run the dashboard
streamlit run dashboard.py

# Or run the terminal agent
python main.py

# Resume a previous session
python main.py <session-id>
```

Get your Anthropic API key at [console.anthropic.com](https://console.anthropic.com).

---

## Project Structure

```
agent_infra/
├── agent.py          # Agent class — tool loop + memory orchestration
├── tools.py          # 11 tools: stock data, insider trades, web, files
├── main.py           # Terminal REPL entry point
├── dashboard.py      # Streamlit dashboard — research + discover + options
├── memory/
│   ├── short_term.py # Sliding window conversation history
│   ├── long_term.py  # SQLite episodic log
│   └── semantic.py   # ChromaDB vector store
├── prompts.md        # Ready-to-use prompt library
├── case_study.md     # Full technical case study
└── requirements.txt
```

---

## The Conviction Score (0–10)

What makes this different from a data dashboard: **judgment built in**.

| Signal | Max | Logic |
|---|---|---|
| Flow strength | 3 pts | Vol/OI ratio — 3× · 5× · 10× |
| Expiry timing | 1 pt | 7–45 days = directional bet |
| Contract type | 1 pt | OTM = pure directional, ITM = possible hedge |
| Fundamentals | 2 pts | Quality of the underlying business |
| Insider alignment | 2 pts | Are insiders buying the same stock? |
| Momentum | 1 pt | Price above/below 50-day MA |
| Analyst consensus | 1 pt | Wall Street aligned with the direction? |

**8–10:** Multiple independent signals aligned. High conviction.
**5–7:** Mixed signals. Wait for price confirmation.
**0–4:** Likely a hedge or noise. Skip.

---

## Data Sources (all free)

| Source | Data | Lag |
|---|---|---|
| Yahoo Finance | Price, fundamentals, options, news | ~15 min |
| SEC EDGAR Form 4 | Every insider buy and sell | 48 hours |
| DuckDuckGo | Web search | Real-time |

---

## Why Not Use a Framework?

LangChain and AutoGen are excellent tools. I didn't use them here because:

1. Writing the loop manually means understanding every step — useful for debugging, extending, and explaining
2. The three-layer memory architecture (short/long/semantic) doesn't map cleanly onto framework abstractions
3. For a portfolio case study, hand-written > framework-wrapped

---

*Built by [Brandon Breon](https://breon.ai) · Not financial advice.*
