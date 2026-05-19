# breon.ai — Case Study Page Copy
## Stock Intelligence Agent

---

### HERO SECTION

**Headline:**
I built the research tool hedge funds pay $25,000/year for.
Using free data. From scratch. In a weekend.

**Subhead:**
An AI agent that reads SEC filings, scores options flow, tracks insider trades, and tells you — in plain English — whether a setup is worth taking.

**[▶ View the Dashboard →](https://alphastack.streamlit.app)**  &nbsp;|&nbsp;  **[Read the Case Study →](https://breon.ai)**  &nbsp;|&nbsp;  **[GitHub →](https://github.com/sooner2w/stock-intelligence-agent)**

---

### THE HOOK (one sentence that earns the scroll)

> Most people look at one signal at a time.
> This tool looks at seven — simultaneously — and scores them into a single number.

---

### WHAT IT DOES
*(3-column card layout)*

**🔍 Research Any Stock**
Type a ticker. Get live price, fundamentals, analyst targets, and a color-coded signal summary — all in one screen. No subscription. No Bloomberg Terminal.

**⚡ Options Flow**
Full options chains with unusual activity flagged automatically. Put/call ratio. Max pain price. IV smile chart. The signals professional traders actually watch.

**📋 Insider Trades**
Pulled directly from SEC EDGAR — the same government database institutional researchers use. Every buy and sell by corporate executives, parsed and scored for conviction. Updated within 48 hours of each trade.

---

### THE CONVICTION SCORE
*(full-width callout section)*

**The part that took the longest to build wasn't the data. It was the judgment.**

When an unusual options trade fires — say, 50,000 contracts bought against 2,000 open interest — the raw signal tells you *something happened*. It doesn't tell you whether to care.

So I built a scoring system that cross-references it against six other independent signals:

```
Options flow strength      ████████░░  
Expiry timing              ██████░░░░  
Insider alignment          ██████████  ← insiders also buying? strong signal.
Fundamentals               ████████░░  
Momentum vs 50-day MA      ██████████  
Analyst consensus          ████░░░░░░  

Conviction Score: 8 / 10 — HIGH
→ Multiple independent signals aligned. Setup worth researching.
```

**8–10 = signals stacked. Worth a hard look.**
**5–7 = interesting. Wait for price to confirm.**
**0–4 = noise or a hedge. Skip it.**

---

### THE DISCOVER ENGINE
*(secondary feature)*

Don't know what to search?

The Discover mode scores 80+ stocks across 7 sectors — Tech, AI/Emerging, Finance, Healthcare, Energy, Consumer, ETFs — and surfaces the top picks automatically. Filter by minimum score, sector, analyst rating, or momentum. The top 3 come up as cards. The rest live in a sortable table.

No ticker required. Just open it and see what's worth researching today.

---

### HOW IT'S BUILT
*(for the technical readers — keep it scannable)*

| Layer | Technology |
|---|---|
| AI brain | Claude Opus 4.7 — manual agentic loop, no frameworks |
| Memory | ChromaDB (semantic) + SQLite (episodic) + sliding window (in-context) |
| Stock data | Yahoo Finance — free, full fundamentals + options |
| Insider data | SEC EDGAR API — free, official, 48hr lag |
| Dashboard | Streamlit + Plotly |
| Language | Python |

**Total monthly cost: $0** (outside Claude API usage)

The agent loop is written by hand — no LangChain, no AutoGen. Every tool call is visible and debuggable. I know exactly what's happening at every step. That was a deliberate choice.

---

### THE DESIGN DECISIONS
*(this is the section that separates you from an engineer who just built a thing)*

**Why build the tool-calling loop manually?**
Frameworks are useful for shipping fast. They're terrible for understanding what's actually happening — and for explaining it to someone else. I wrote every line of the agent loop so I can reason about it, debug it, and teach it. That's a different skill than using a library.

**Why a conviction score instead of just showing the signals?**
Because information overload is its own problem. Showing someone 7 charts and saying "figure it out" isn't a product — it's a data dump. The conviction score exists because the hardest design problem wasn't the engineering. It was deciding: *what does the person looking at this screen actually need to know, and in what form do they need to know it?*

**Why free data sources?**
Because the question "what's already public and underused?" is more interesting than "what can I pay for?" SEC insider filing data is legally required to be public. Yahoo Finance publishes full options chains. The data gap was never real — the synthesis gap was. That's a pattern I look for in every problem.

---

### THE ONE-LINER
*(pull quote / shareable card)*

> "The designer-builder gap is real. Most designers can't build.
> Most engineers don't think about the person using the thing.
> This project is what happens when you do both."
>
> — Brandon Breon

---

### CALL TO ACTION

**If you're building something that needs both:**

The product sense to know what to build.
The technical depth to actually build it.
And the ability to explain the decisions in between.

**[Let's talk →]   [breon.ai →]   [GitHub →](https://github.com/sooner2w/stock-intelligence-agent)**

---
*Stack: Python · Claude API · SEC EDGAR · Yahoo Finance · ChromaDB · Streamlit*
*Built by Brandon Breon*
