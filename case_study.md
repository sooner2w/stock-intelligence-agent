# Case Study: Stock Intelligence Agent
### Building a Bloomberg-Level Research Tool with Free Data and AI — From Scratch

---

## The Problem

Retail investors operate at a structural disadvantage.

The people managing billions — hedge funds, proprietary trading desks, institutional analysts — have access to tools that cost $25,000/year or more. Bloomberg Terminal. Refinitiv. Alternative data feeds built from satellite imagery and credit card transactions. By the time a signal reaches CNBC or a Reddit thread, the trade has already been made.

Most people assume this gap is unbridgeable without a Wall Street salary.

I wanted to find out if that was actually true.

---

## The Hypothesis

The SEC publishes every insider trade within 48 hours — for free.
Yahoo Finance publishes full options chains, fundamentals, and analyst targets — for free.
Claude (Anthropic's AI) can reason across all of it simultaneously — and explain its logic.

The data was never the problem. **The problem was synthesis.** No one had connected these sources into a single tool that asked: *what are all the signals saying right now, together, about this stock?*

That's what I built.

---

## What I Built

**A full-stack AI stock research dashboard** with three integrated layers:

### 1. AI Agent Infrastructure (Python)
Not a wrapper around someone else's agent framework. Built from scratch:
- **Manual tool-calling loop** — Claude decides which tools to invoke, in what order, based on your question. The loop runs until it has a complete answer.
- **Three-layer memory** — short-term (sliding conversation window), long-term (SQLite episodic log survives session restarts), semantic (ChromaDB vector store finds relevant past context by meaning, not keyword).
- **11 live tools** — web search, URL fetch, file read/write, stock data, stock comparison, insider trades (SEC EDGAR), insider buying scan, memory save/search.

This means you can ask: *"Get insider trades for META, pull its fundamentals, search the web for recent news, and write me a full investment thesis to my Desktop"* — and the agent executes all of it autonomously, in sequence, with memory of what you've discussed before.

### 2. Real-Time Stock Research Dashboard (Streamlit + Plotly)
A visual dashboard that surfaces everything in one screen per ticker:
- Live price, 3-month chart with 50d MA and analyst price target overlay
- Full fundamentals table (P/E, forward P/E, PEG, revenue growth, margins, ROE, free cash flow, debt/equity, dividend yield)
- Signal summary bar — 5 color-coded cards (valuation, growth, analyst, momentum, short interest)
- SEC EDGAR insider trades — parsed from raw XML Form 4 filings, with buy/sell ratio and dollar totals
- Recent news headlines with source links

### 3. Options Flow Analysis
The part most tools charge for:
- Full options chain (calls and puts) for any expiration date
- Put/call ratio with plain-English interpretation
- **Max pain** price calculation — where market makers profit most at expiration
- **IV smile chart** — implied volatility across strikes, showing where fear is concentrated
- **Open interest by strike** — where the largest positions are sitting
- **⚡ Unusual activity detection** — flags contracts where volume exceeds open interest by 3× or more (fresh money entering the market, not positions being closed)

### 4. Discover Engine
A stock scanner that scores a universe of 80+ stocks across 7 sectors on 5 independent signals — valuation, growth, analyst consensus, momentum, and margin — and surfaces the top picks automatically. No ticker required.

### 5. Conviction Scoring System (0–10)
The centerpiece of the options flow module. Rather than showing raw unusual activity and leaving interpretation to the user, every flagged contract is scored across 7 independent signals:

| Signal | Logic |
|---|---|
| **Flow strength** | Volume/OI ratio — 3× = fresh position, 10× = aggressive entry |
| **Expiry timing** | 7–45 days = directional bet. Under 7 = closing. Over 45 = hedge. |
| **Contract type** | OTM = pure directional. ITM = could be protection on existing shares. |
| **Fundamentals** | Is the underlying stock actually a quality business? |
| **Insider alignment** | Are insiders buying the same stock the options sweep is pointing at? |
| **Momentum** | Is price above or below the 50-day MA in the direction of the bet? |
| **Analyst consensus** | Does Wall Street's aggregate view align with the options direction? |

A score of 8–10 means multiple independent, unrelated data sources are pointing in the same direction simultaneously. That's not noise. That's a signal worth researching.

---

## The Technical Stack

| Layer | Technology | Why |
|---|---|---|
| AI brain | Claude Opus 4.7 (Anthropic) | Best reasoning model available; adaptive thinking for complex multi-step analysis |
| Vector memory | ChromaDB + sentence-transformers | Local, free, no API cost — semantic search over past research |
| Episodic memory | SQLite | Zero setup, survives session restarts, queryable |
| Stock data | yfinance (Yahoo Finance) | Free, full fundamentals + options chains + news |
| Insider data | SEC EDGAR API | Free, official, 48-hour lag on real trades |
| Web search | DuckDuckGo API | No key required |
| Dashboard | Streamlit + Plotly | Fast to ship, professional output |
| Language | Python | Ecosystem fit for data + AI |

**Total infrastructure cost: $0/month** (beyond the Claude API calls for the agent).

---

## The Design Decisions

### Why not use LangChain or AutoGen?
Every major AI framework abstracts the agent loop away from you. That's useful for shipping fast. It's terrible for understanding what's actually happening — and for debugging when it breaks. I wrote the tool-calling loop manually so every step is visible and controllable. This also means I can explain exactly how it works to anyone, which matters for the case study and for future development.

### Why three memory layers instead of one?
Because human memory doesn't work as a single list. Working memory (what's in front of you), episodic memory (what happened last Tuesday), and semantic memory (what do I know about this topic) serve different functions. Building them separately means the agent can do all three: stay focused in a conversation, resume a session from weeks ago, and surface relevant past research automatically.

### Why SEC EDGAR instead of a paid data provider?
Insider trading data is legally required to be public and free. Most retail investors don't look at it because it requires parsing federal XML filings. The raw data is there — what was missing was a tool that made it readable. Making free data accessible is often more valuable than buying expensive data.

### Why a conviction score instead of just showing the signal?
Because showing data is not the same as helping someone make a decision. A raw options volume number tells you something happened. A conviction score that cross-references it against insider activity, fundamentals, and momentum answers the question: *should I care about this?* The design intent was to remove guesswork, not add more information to sort through.

---

## What This Demonstrates

**For employers and collaborators:**

This project sits at the exact intersection that's hardest to find in one person:

- **Systems thinking** — the three-layer memory architecture, the conviction scoring model, the way signals feed into each other
- **Product thinking** — the dashboard wasn't built because it was technically interesting. It was built because data without presentation is useless. Every design decision (the signal cards, the conviction score chips, the unusual activity expander) was made around the question: *what does the person looking at this screen actually need to know?*
- **Technical execution** — zero frameworks, zero boilerplate. SEC XML parsing, vector embeddings, agentic loops, real-time financial data, custom scoring models — all built from scratch in a single project
- **Resourcefulness** — the entire data stack costs nothing. The instinct to ask "what's free and underused?" before reaching for an expensive API is the same instinct that makes engineers valuable in early-stage environments

---

## What's Next

This is a proof-of-concept built to demonstrate capability, not a shipped product. The natural extensions:

- **13F hedge fund holdings** — SEC filings revealing what major funds hold, updated quarterly
- **Earnings call transcript analysis** — agent reads the full transcript and identifies management tone shifts, guidance language, and analyst reaction
- **Short interest trend** — FINRA publishes bi-monthly short data; rising short interest is an early warning signal
- **Email/Slack alerts** — when a high-conviction (8+) unusual activity event fires, notify immediately
- **Multi-ticker portfolio view** — conviction scoring across an entire watchlist simultaneously

---

## One Line

> I built the research stack a hedge fund analyst uses — out of public data, an AI agent, and Python — in a weekend. This is what the designer-builder combination looks like.

---

*Built by Brandon Breon · breon.ai*
*Stack: Python · Claude API (Anthropic) · SEC EDGAR · Yahoo Finance · ChromaDB · Streamlit*
*All data sources are free and public. Not financial advice.*
