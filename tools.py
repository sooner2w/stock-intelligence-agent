import urllib.request
import urllib.parse
import urllib.error
import json
import re
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

# ------------------------------------------------------------------ #
# Tool schemas — what Claude sees

TOOLS = [
    {
        "name": "save_memory",
        "description": (
            "Persist an important fact, preference, or piece of information to "
            "long-term semantic memory so it can be recalled in future conversations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The exact text to remember."},
                "category": {
                    "type": "string",
                    "description": "Short label for the memory (e.g. 'preference', 'fact', 'goal').",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "search_memory",
        "description": (
            "Search semantic memory for facts related to a query. "
            "Use this before answering questions about the user's history or preferences."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language description of what to look for."},
                "n_results": {"type": "integer", "description": "Max results to return (default 3).", "default": 3},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_current_time",
        "description": "Return the current UTC date and time.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo and return the top results. "
            "Use this for current events, facts, or anything you're unsure about."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "max_results": {"type": "integer", "description": "Max results to return (default 5).", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch the text content of a webpage. "
            "Use this to read articles, documentation, or any URL the user mentions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to fetch."},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 4000).",
                    "default": 4000,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a local file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_stock_data",
        "description": (
            "Retrieve real-time and historical stock data for a ticker symbol. "
            "Returns price, fundamentals (P/E, market cap, EPS, revenue), recent news headlines, "
            "and price history. Use this for stock research and analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, NVDA, TSLA, SPY).",
                },
                "include_history": {
                    "type": "boolean",
                    "description": "Include 30-day price history (default false).",
                    "default": False,
                },
                "include_news": {
                    "type": "boolean",
                    "description": "Include recent news headlines (default true).",
                    "default": True,
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "compare_stocks",
        "description": "Compare key metrics for multiple ticker symbols side by side.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols to compare (e.g. ['AAPL', 'MSFT', 'GOOGL']).",
                },
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "get_insider_trades",
        "description": (
            "Fetch recent SEC Form 4 insider trading filings for a stock ticker. "
            "Shows who bought or sold, how many shares, at what price, and total value. "
            "Insider buying is a strong early signal — executives rarely buy their own stock unless they expect it to rise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL, NVDA)."},
                "days": {"type": "integer", "description": "How many days back to look (default 90).", "default": 90},
                "buys_only": {"type": "boolean", "description": "Only show purchases, not sales (default false).", "default": False},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "scan_insider_buying",
        "description": (
            "Scan SEC EDGAR for large insider PURCHASES filed in the last N days across the whole market. "
            "Filters for open-market buys above a minimum dollar value. "
            "This is how you find stocks where insiders are putting their own money in — before the news hits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "How many days back to scan (default 7, max 30).", "default": 7},
                "min_value": {"type": "integer", "description": "Minimum transaction value in USD to include (default 100000).", "default": 100000},
                "max_results": {"type": "integer", "description": "Max filings to return (default 20).", "default": 20},
            },
            "required": [],
        },
    },
    {
        "name": "write_file",
        "description": "Write text content to a local file, creating it if it doesn't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."},
                "content": {"type": "string", "description": "Text content to write."},
            },
            "required": ["path", "content"],
        },
    },
]

# ------------------------------------------------------------------ #
# Tool executor


def execute_tool(name: str, tool_input: dict, semantic_memory) -> str:
    if name == "save_memory":
        text = tool_input["text"]
        category = tool_input.get("category", "general")
        semantic_memory.add(text, metadata={"category": category})
        return f"Memory saved (category: {category})."

    elif name == "search_memory":
        query = tool_input["query"]
        n = tool_input.get("n_results", 3)
        results = semantic_memory.search(query, n_results=n)
        if not results:
            return "No relevant memories found."
        numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(results))
        return f"Found {len(results)} memories:\n{numbered}"

    elif name == "get_current_time":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    elif name == "web_search":
        return _web_search(tool_input["query"], tool_input.get("max_results", 5))

    elif name == "fetch_url":
        return _fetch_url(tool_input["url"], tool_input.get("max_chars", 4000))

    elif name == "read_file":
        return _read_file(tool_input["path"])

    elif name == "write_file":
        return _write_file(tool_input["path"], tool_input["content"])

    elif name == "get_stock_data":
        return _get_stock_data(
            tool_input["ticker"],
            tool_input.get("include_history", False),
            tool_input.get("include_news", True),
        )

    elif name == "compare_stocks":
        return _compare_stocks(tool_input["tickers"])

    elif name == "get_insider_trades":
        return _get_insider_trades(
            tool_input["ticker"],
            tool_input.get("days", 90),
            tool_input.get("buys_only", False),
        )

    elif name == "scan_insider_buying":
        return _scan_insider_buying(
            tool_input.get("days", 7),
            tool_input.get("min_value", 100_000),
            tool_input.get("max_results", 20),
        )

    else:
        return f"Unknown tool: {name}"


# ------------------------------------------------------------------ #
# Implementations

def _web_search(query: str, max_results: int) -> str:
    """DuckDuckGo instant-answer API — no key required."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agent-infra/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Search failed: {e}"

    results = []

    # Abstract (Wikipedia-style summary)
    if data.get("Abstract"):
        results.append(f"[Summary] {data['Abstract']} ({data.get('AbstractURL', '')})")

    # Related topics
    for topic in data.get("RelatedTopics", [])[:max_results]:
        if isinstance(topic, dict) and topic.get("Text"):
            url_ref = topic.get("FirstURL", "")
            results.append(f"- {topic['Text']} ({url_ref})")

    if not results:
        return (
            f"No instant-answer results for '{query}'. "
            "Try fetch_url with a specific page, or rephrase the query."
        )

    return "\n".join(results[:max_results + 1])


def _fetch_url(url: str, max_chars: int) -> str:
    """Fetch a URL and return stripped plain text."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Fetch failed: {e}"

    # Strip HTML tags
    text = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[truncated — {len(text)} total chars]"
    return text


def _read_file(path: str) -> str:
    try:
        return Path(path).expanduser().read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Read failed: {e}"


def _write_file(path: str, content: str) -> str:
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {p}."
    except Exception as e:
        return f"Write failed: {e}"


def _get_stock_data(ticker: str, include_history: bool, include_news: bool) -> str:
    if not _YF_AVAILABLE:
        return "yfinance not installed. Run: pip3 install yfinance"

    try:
        t = yf.Ticker(ticker.upper())
        info = t.info
    except Exception as e:
        return f"Failed to fetch {ticker}: {e}"

    def _fmt(val, prefix="", suffix="", decimals=2):
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{prefix}{val:,.{decimals}f}{suffix}"
        if isinstance(val, int):
            return f"{prefix}{val:,}{suffix}"
        return str(val)

    def _fmt_large(val):
        if val is None:
            return "N/A"
        if val >= 1_000_000_000_000:
            return f"${val/1_000_000_000_000:.2f}T"
        if val >= 1_000_000_000:
            return f"${val/1_000_000_000:.2f}B"
        if val >= 1_000_000:
            return f"${val/1_000_000:.2f}M"
        return f"${val:,.0f}"

    def _pct(val, decimals=1):
        if val is None:
            return "N/A"
        return f"{val * 100:.{decimals}f}%"

    lines = [
        f"=== {info.get('longName', ticker.upper())} ({ticker.upper()}) ===",
        f"Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}",
        "",
        "--- Price ---",
        f"Current:     {_fmt(info.get('currentPrice'), '$')}",
        f"Open:        {_fmt(info.get('open'), '$')}",
        f"Day Range:   {_fmt(info.get('dayLow'), '$')} – {_fmt(info.get('dayHigh'), '$')}",
        f"52w Range:   {_fmt(info.get('fiftyTwoWeekLow'), '$')} – {_fmt(info.get('fiftyTwoWeekHigh'), '$')}",
        f"50d MA:      {_fmt(info.get('fiftyDayAverage'), '$')}",
        f"200d MA:     {_fmt(info.get('twoHundredDayAverage'), '$')}",
        "",
        "--- Fundamentals ---",
        f"Market Cap:  {_fmt_large(info.get('marketCap'))}",
        f"P/E (TTM):   {_fmt(info.get('trailingPE'))}",
        f"Fwd P/E:     {_fmt(info.get('forwardPE'))}",
        f"PEG Ratio:   {_fmt(info.get('pegRatio'))}",
        f"P/S Ratio:   {_fmt(info.get('priceToSalesTrailing12Months'))}",
        f"P/B Ratio:   {_fmt(info.get('priceToBook'))}",
        f"EPS (TTM):   {_fmt(info.get('trailingEps'), '$')}",
        f"Fwd EPS:     {_fmt(info.get('forwardEps'), '$')}",
        f"Revenue:     {_fmt_large(info.get('totalRevenue'))}",
        f"Rev Growth:  {_pct(info.get('revenueGrowth'))}",
        f"Gross Margin:{_pct(info.get('grossMargins'))}",
        f"Profit Mgn:  {_pct(info.get('profitMargins'))}",
        f"Debt/Equity: {_fmt(info.get('debtToEquity'))}",
        f"ROE:         {_pct(info.get('returnOnEquity'))}",
        f"Free CF:     {_fmt_large(info.get('freeCashflow'))}",
        "",
        "--- Dividend ---",
        f"Yield:       {_pct(info.get('dividendYield'), decimals=2)}",
        f"Payout Ratio:{_pct(info.get('payoutRatio'))}",
        "",
        "--- Analyst ---",
        f"Recommendation: {info.get('recommendationKey', 'N/A').upper()}",
        f"Target Price:   {_fmt(info.get('targetMeanPrice'), '$')} (low {_fmt(info.get('targetLowPrice'), '$')} / high {_fmt(info.get('targetHighPrice'), '$')})",
        f"# Analysts:     {info.get('numberOfAnalystOpinions', 'N/A')}",
        "",
        "--- Ownership ---",
        f"Insider Own:  {_pct(info.get('heldPercentInsiders'))}",
        f"Inst. Own:    {_pct(info.get('heldPercentInstitutions'))}",
        f"Short %:      {_pct(info.get('shortPercentOfFloat'))}",
        f"Beta:         {_fmt(info.get('beta'))}",
    ]

    if include_history:
        try:
            hist = t.history(period="1mo")
            if not hist.empty:
                lines += ["", "--- 30-Day Price History (weekly) ---"]
                sampled = hist["Close"].resample("W").last().dropna()
                for date, price in sampled.items():
                    lines.append(f"  {date.strftime('%Y-%m-%d')}: ${price:.2f}")
        except Exception:
            pass

    if include_news:
        try:
            news = t.news
            if news:
                lines += ["", "--- Recent News ---"]
                for item in news[:5]:
                    title = item.get("content", {}).get("title") or item.get("title", "")
                    if title:
                        lines.append(f"• {title}")
        except Exception:
            pass

    return "\n".join(lines)


def _compare_stocks(tickers: list[str]) -> str:
    if not _YF_AVAILABLE:
        return "yfinance not installed. Run: pip3 install yfinance"

    headers = ["Ticker", "Price", "Mkt Cap", "P/E", "Fwd P/E", "EPS", "Rev Growth", "Margin", "Analyst"]
    rows = []

    for sym in tickers:
        try:
            info = yf.Ticker(sym.upper()).info
            rev_growth = info.get("revenueGrowth")
            margin = info.get("profitMargins")
            rows.append([
                sym.upper(),
                f"${info.get('currentPrice', 'N/A')}",
                _fmt_large_inline(info.get("marketCap")),
                f"{info.get('trailingPE', 'N/A')}",
                f"{info.get('forwardPE', 'N/A')}",
                f"${info.get('trailingEps', 'N/A')}",
                f"{rev_growth*100:.1f}%" if rev_growth else "N/A",
                f"{margin*100:.1f}%" if margin else "N/A",
                info.get("recommendationKey", "N/A").upper(),
            ])
        except Exception as e:
            rows.append([sym.upper()] + [f"Error: {e}"] + [""] * 7)

    col_widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)

    lines = [fmt.format(*headers), "-" * sum(col_widths + [2] * (len(headers) - 1))]
    for row in rows:
        lines.append(fmt.format(*row))

    return "\n".join(lines)


_EDGAR_HEADERS = {
    "User-Agent": "Brandon Breon brandonbreon@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}

_EFTS_HEADERS = {
    "User-Agent": "Brandon Breon brandonbreon@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}


def _edgar_get(url: str, headers: dict = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or _EDGAR_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def _ticker_to_cik(ticker: str) -> str:
    """Map ticker symbol to zero-padded 10-digit CIK string."""
    data = json.loads(_edgar_get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=_EFTS_HEADERS,
    ))
    ticker_up = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_up:
            return f"{entry['cik_str']:010d}"
    return ""


def _parse_form4_xml(xml_bytes: bytes) -> list[dict]:
    """Extract transactions from a Form 4 XML filing."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    ns = ""
    owner_name = root.findtext(f"{ns}reportingOwner/{ns}reportingOwnerId/{ns}rptOwnerName") or "Unknown"
    title = root.findtext(f"{ns}reportingOwner/{ns}reportingOwnerRelationship/{ns}officerTitle") or ""
    is_director = root.findtext(f"{ns}reportingOwner/{ns}reportingOwnerRelationship/{ns}isDirector") or "0"
    is_officer = root.findtext(f"{ns}reportingOwner/{ns}reportingOwnerRelationship/{ns}isOfficer") or "0"

    role = title if title else ("Director" if is_director == "1" else ("Officer" if is_officer == "1" else "Insider"))

    trades = []
    for txn in root.findall(f"nonDerivativeTable/nonDerivativeTransaction"):
        date = txn.findtext("transactionDate/value") or ""
        shares_str = txn.findtext("transactionAmounts/transactionShares/value") or "0"
        price_str = txn.findtext("transactionAmounts/transactionPricePerShare/value") or "0"
        code = txn.findtext("transactionAmounts/transactionAcquiredDisposedCode/value") or ""
        shares_after = txn.findtext("postTransactionAmounts/sharesOwnedFollowingTransaction/value") or "0"

        try:
            shares = float(shares_str)
            price = float(price_str)
            value = shares * price
            owned_after = float(shares_after)
        except ValueError:
            continue

        if code not in ("A", "D"):
            continue

        trades.append({
            "date": date,
            "name": owner_name,
            "role": role,
            "action": "BUY" if code == "A" else "SELL",
            "shares": shares,
            "price": price,
            "value": value,
            "owned_after": owned_after,
        })

    return trades


def _get_insider_trades(ticker: str, days: int, buys_only: bool) -> str:
    cik = _ticker_to_cik(ticker)
    if not cik:
        return f"Ticker '{ticker}' not found in SEC EDGAR."

    try:
        sub_data = json.loads(_edgar_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    except Exception as e:
        return f"Failed to fetch EDGAR submissions: {e}"

    recent = sub_data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    all_trades = []

    cik_int = int(cik)
    for form, date, acc in zip(forms, dates, accessions):
        if form != "4":
            continue
        if date < cutoff:
            continue

        acc_nodash = acc.replace("-", "")
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}"
        try:
            dir_html = _edgar_get(f"{base_url}/", headers=_EFTS_HEADERS).decode("utf-8", errors="replace")
            xml_files = re.findall(rf'/Archives/edgar/data/{cik_int}/{acc_nodash}/([^"]+\.xml)', dir_html)
            xml_file = next((f for f in xml_files if not f.startswith("R") and "xsl" not in f.lower()), None)
            if not xml_file:
                continue
            xml_bytes = _edgar_get(f"{base_url}/{xml_file}", headers=_EFTS_HEADERS)
            trades = _parse_form4_xml(xml_bytes)
            for t in trades:
                t["filed"] = date
            all_trades.extend(trades)
        except Exception:
            continue

    if buys_only:
        all_trades = [t for t in all_trades if t["action"] == "BUY"]

    if not all_trades:
        label = "purchases" if buys_only else "trades"
        return f"No insider {label} found for {ticker.upper()} in the last {days} days."

    all_trades.sort(key=lambda x: x["date"], reverse=True)

    lines = [f"=== Insider Trades: {ticker.upper()} (last {days} days) ===", ""]
    for t in all_trades:
        flag = " *** LARGE BUY ***" if t["action"] == "BUY" and t["value"] > 500_000 else ""
        lines.append(
            f"[{t['date']}] {t['action']:4s}  {t['name']} ({t['role']})"
        )
        lines.append(
            f"          {t['shares']:>12,.0f} shares @ ${t['price']:>8.2f}  =  ${t['value']:>12,.0f}{flag}"
        )
        lines.append(
            f"          Owns after: {t['owned_after']:,.0f} shares"
        )
        lines.append("")

    buy_total = sum(t["value"] for t in all_trades if t["action"] == "BUY")
    sell_total = sum(t["value"] for t in all_trades if t["action"] == "SELL")
    lines.append(f"--- Summary ---")
    lines.append(f"Total insider buying:  ${buy_total:>14,.0f}")
    lines.append(f"Total insider selling: ${sell_total:>14,.0f}")
    ratio = buy_total / sell_total if sell_total else float("inf")
    lines.append(f"Buy/Sell ratio: {ratio:.2f}x  {'(BULLISH SIGNAL)' if ratio > 1 else '(bearish signal)'}")

    return "\n".join(lines)


def _scan_insider_buying(days: int, min_value: int, max_results: int) -> str:
    """Scan EDGAR for large open-market insider purchases market-wide."""
    days = min(days, 30)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    search_url = (
        f"https://efts.sec.gov/LATEST/search-index?forms=4"
        f"&dateRange=custom&startdt={start}&enddt={end}"
        f"&_source=file_date,period_of_report,entity_name,file_num"
        f"&from=0&hits.hits.total.value=true&hits.hits._source.period_of_report=true"
    )

    try:
        req = urllib.request.Request(search_url, headers=_EFTS_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception as e:
        return f"EDGAR search failed: {e}"

    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        return "No recent Form 4 filings found."

    results = []
    checked = 0

    for hit in hits[:60]:
        if len(results) >= max_results:
            break
        checked += 1

        src = hit.get("_source", {})
        entity = src.get("entity_name", ["Unknown"])[0] if isinstance(src.get("entity_name"), list) else src.get("entity_name", "Unknown")
        file_date = src.get("file_date", "")

        acc = hit.get("_id", "")
        if not acc:
            continue

        acc_nodash = acc.replace("-", "")
        parts = acc.split("-")
        if len(parts) < 2:
            continue
        cik_raw = parts[0].lstrip("0") or "0"

        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_raw}/{acc_nodash}"
        try:
            dir_html = _edgar_get(f"{base_url}/", headers=_EFTS_HEADERS).decode("utf-8", errors="replace")
            xml_files = re.findall(rf'/Archives/edgar/data/{cik_raw}/{acc_nodash}/([^"]+\.xml)', dir_html)
            xml_file = next((f for f in xml_files if not f.startswith("R") and "xsl" not in f.lower()), None)
            if not xml_file:
                continue
            xml_bytes = _edgar_get(f"{base_url}/{xml_file}", headers=_EFTS_HEADERS)
            trades = _parse_form4_xml(xml_bytes)
        except Exception:
            continue

        buys = [t for t in trades if t["action"] == "BUY" and t["value"] >= min_value]
        for t in buys:
            results.append({
                "entity": entity,
                "filed": file_date,
                **t,
            })

    if not results:
        return (
            f"No insider purchases >= ${min_value:,} found in the last {days} days "
            f"(scanned {checked} filings). Try lowering min_value or increasing days."
        )

    results.sort(key=lambda x: x["value"], reverse=True)

    lines = [
        f"=== Insider Buying Scan: last {days} days, min ${min_value:,} ===",
        f"Found {len(results)} qualifying purchases\n",
    ]
    for r in results[:max_results]:
        lines.append(f"{'BUY':4s} {r['entity']}")
        lines.append(f"     {r['name']} ({r['role']})")
        lines.append(f"     {r['shares']:>10,.0f} shares @ ${r['price']:.2f}  =  ${r['value']:>12,.0f}")
        lines.append(f"     Filed: {r['filed']}  |  Trade date: {r['date']}")
        lines.append("")

    return "\n".join(lines)


def _fmt_large_inline(val) -> str:
    if val is None:
        return "N/A"
    if val >= 1_000_000_000_000:
        return f"${val/1_000_000_000_000:.1f}T"
    if val >= 1_000_000_000:
        return f"${val/1_000_000_000:.1f}B"
    return f"${val/1_000_000:.0f}M"
