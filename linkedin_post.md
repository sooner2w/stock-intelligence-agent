# LinkedIn Launch Post

---

## VERSION 1 — The story (best for engagement)

I spent a weekend building the research tool hedge funds pay $25,000/year for.

Using free public data.

Here's what it does:

→ Pulls real insider trades directly from SEC filings (48hr lag, same data institutions use)
→ Scores options unusual activity against 7 independent signals
→ Surfaces a conviction score — 0 to 10 — so you know whether to act or ignore
→ Scans 80+ stocks across sectors automatically. No ticker needed.

The whole stack: Python, Claude API, SEC EDGAR, Yahoo Finance.
Monthly data cost: $0.

Live now: alphastack.streamlit.app
Code: github.com/sooner2w/stock-intelligence-agent

This is what the designer-builder combination looks like.

---

## VERSION 2 — The hook (best for reach, shorter)

Most retail investors lose because they look at one signal at a time.

Institutions stack them.

I built a tool that does the stacking automatically — insider trades, options flow, fundamentals, momentum — and gives you a conviction score out of 10.

Free. Live. Built from scratch.

→ alphastack.streamlit.app

---

## VERSION 3 — The technical credibility post (best for recruiting)

I built an AI stock research agent. Here's the architecture:

**Memory layer:**
- Short-term: sliding window conversation history
- Long-term: SQLite episodic log (survives session restarts)
- Semantic: ChromaDB vector store (finds context by meaning, not keyword)

**Tool loop:** Written by hand. No LangChain. No AutoGen.
Claude decides which tools to invoke, in what order, until it has a complete answer.

**Data layer:**
- Yahoo Finance: price, fundamentals, options chains
- SEC EDGAR: Form 4 insider trades parsed from raw XML
- DuckDuckGo: web search

**Dashboard:** Streamlit + Plotly. Dark theme. Conviction scoring built in.

**Total infrastructure cost:** $0/month in data.

Live: alphastack.streamlit.app
Code: github.com/sooner2w/stock-intelligence-agent
Case study: breon.ai

---

## POSTING NOTES

- Post Version 1 first — it tells a story and will get the most shares
- Post at 8–9am Tuesday or Wednesday (highest LinkedIn engagement windows)
- First comment: drop the Loom video link as a reply to your own post — LinkedIn deprioritizes external links in the post body, putting it in comments gets more reach
- Tag: #buildinpublic #python #ai #fintech #agents

