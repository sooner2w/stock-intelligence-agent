# Agent Prompts

Copy-paste these directly into `python3 main.py` to test and explore the agent.

---

## Memory

```
My name is Brandon and I'm building AI agents to stand out in the job market.
```
```
Remember that I prefer concise answers and bullet points over long paragraphs.
```
```
What do you know about me?
```
```
What have we talked about before?
```
```
Save this for later: my agent project lives at ~/agent_infra
```

---

## Web Search

```
Search for the latest news on AI agents and summarize what you find.
```
```
What is ChromaDB and why would someone use it?
```
```
Search for: best practices for building LLM tool calling loops
```
```
Who are the top companies building AI agent infrastructure right now?
```
```
Search for recent papers on retrieval-augmented generation (RAG).
```

---

## Fetch URL

```
Fetch this page and give me the key points: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
```
```
Read this URL and summarize it in 3 bullet points: [paste any URL]
```
```
Go to https://pypi.org/project/chromadb/ and tell me the latest version and what changed.
```

---

## File Operations

```
Write a file called ~/Desktop/agent_notes.txt with a summary of what this agent can do.
```
```
Read the file at ~/agent_infra/agent.py and explain how the tool calling loop works.
```
```
Create a file at ~/agent_infra/ideas.md and fill it with 10 ideas for tools I could add to this agent.
```
```
Read ~/agent_infra/tools.py and tell me which tool is most complex and why.
```

---

## Multi-step (chains multiple tools)

```
Search the web for "top AI agent frameworks 2025", then save the top 3 findings to memory.
```
```
Look up what sentence-transformers is, then write a 1-paragraph explanation to ~/Desktop/explainer.txt
```
```
Search for AI agent job postings, summarize the most common skills they ask for, and save that to memory.
```
```
Read my file ~/agent_infra/agent.py, then search the web for ways to improve the architecture, then write your recommendations to ~/agent_infra/improvements.md
```

---

## Self-reflection / meta

```
What tools do you have available?
```
```
Walk me through exactly what happens when I send you a message — step by step.
```
```
What would make you more useful as an agent?
```
```
What are your limitations right now?
```

---

## Stock Research

### Single stock deep-dives
```
Pull full data on NVDA and give me your analysis — is it a buy right now?
```
```
Get me everything on AAPL including 30-day price history and recent news.
```
```
What does the TSLA data look like? Focus on fundamentals and analyst targets.
```
```
Pull data on META and tell me if the valuation makes sense given its growth rate.
```
```
Get MSFT data and compare its P/E and forward P/E to its 5-year average.
```

### Comparisons
```
Compare NVDA, AMD, and INTC side by side and tell me which has the best risk/reward.
```
```
Compare AAPL, MSFT, GOOGL, and META on fundamentals. Which would you buy and why?
```
```
Compare SPY, QQQ, and VTI — which ETF has the best profile for long-term holding?
```
```
Compare AMZN and SHOP. Which is growing faster relative to its valuation?
```

### Screening and ideas
```
Search the web for "most undervalued tech stocks 2025" then pull data on the top 3 mentioned.
```
```
Search for "high insider buying stocks this month" and pull data on the first ticker you find.
```
```
Search for "AI infrastructure stocks to watch" and compare the top 3 you find.
```
```
Look up "stocks with low PEG ratio and high revenue growth" and analyze what comes up.
```
```
Search for "small cap stocks with strong earnings growth 2025" and pull data on two of them.
```

### Insider trading (SEC Form 4 — real data, 48hr lag)
```
Show me insider trades for NVDA over the last 90 days.
```
```
Show me only insider PURCHASES for AAPL in the last 60 days.
```
```
Get insider trades for TSLA and tell me if the buy/sell ratio is bullish or bearish.
```
```
Scan the whole market for insider purchases over $500,000 filed in the last 7 days.
```
```
Scan for large insider buys in the last 14 days with a minimum value of $1,000,000.
```
```
Get insider trades for META, then pull full stock data, then give me a complete picture of whether insiders think it's a buy.
```
```
Scan for insider buying this week, then pull stock data on the top 3 by purchase size, then write a report to ~/Desktop/insider_report.md
```

### Multi-step research workflows
```
Pull data on NVDA, AMD, and INTC. Compare them. Then write a full investment thesis to ~/Desktop/chip_stocks.md
```
```
Get data on TSLA. Search the web for recent Tesla news. Then give me a bull case and bear case.
```
```
Pull data on 5 stocks I should know about in the AI space: NVDA, PLTR, AI, SOUN, IONQ. Compare them and save your top pick to memory.
```
```
Search for "Warren Buffett portfolio 2025", find 3 stocks he holds, pull data on each, and write a summary to ~/Desktop/buffett_picks.md
```
```
Get data on my watchlist: AAPL, NVDA, MSFT, AMZN, GOOGL. Rank them by forward P/E from lowest to highest and tell me which is cheapest relative to growth.
```

---

## Ideas for new tools to add next

| Tool | What it does |
|---|---|
| `run_python` | Execute a Python snippet and return stdout |
| `run_bash` | Run a shell command and return output |
| `list_directory` | List files in a folder |
| `google_calendar` | Read/write calendar events via Google API |
| `send_email` | Send an email via Gmail or SMTP |
| `scrape_links` | Extract all links from a fetched page |
| `summarize_file` | Chunk + summarize a large file that won't fit in context |
| `image_describe` | Pass an image to Claude vision and describe it |
| `set_reminder` | Write a timed reminder to a local cron or launchd job |
| `wikipedia_search` | Pull a Wikipedia article summary directly |
