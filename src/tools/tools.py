#WEBSEARCH TOOL

from langchain.tools import tool 
import requests
from dotenv import load_dotenv
import os
from tavily import TavilyClient
try:
    from rich import print
except ImportError:
    pass
from bs4 import BeautifulSoup
from readability import Document
import trafilatura
import re 


load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """
    Search the web for recent and reliable information on a topic.
    Returns titles, URLs, and snippets.
    """
    print(f"  [Tool: web_search] Querying Tavily: '{query}'...", flush=True)
    results = tavily.search(query=query, max_results=5)

    out = []

    for r in results['results']:
        out.append(
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content'][:300]}\n"
        )

    print(f"  [Tool: web_search] Retrieved {len(results.get('results', []))} results.", flush=True)
    return "\n".join(out)

@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract clean readable content from a URL.
    Uses multiple extraction strategies for better reliability.
    """
    print(f"  [Tool: scrape_url] Fetching URL: {url}...", flush=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    try:
        # ── Fetch page ─────────────────────────────────────
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        html = response.text

        # ──────────────────────────────────────────────────
        # Strategy 1 → trafilatura (BEST for articles/blogs)
        # ──────────────────────────────────────────────────
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False
        )

        if extracted and len(extracted.strip()) > 200:
            cleaned = re.sub(r'\s+', ' ', extracted)
            print(f"  [Tool: scrape_url] Strategy 1 (Trafilatura) succeeded ({len(cleaned)} chars extracted).", flush=True)
            return cleaned[:5000]

        print(f"  [Tool: scrape_url] Strategy 1 yielded insufficient text (<200 chars). Trying Strategy 2 (Readability)...", flush=True)
        # ──────────────────────────────────────────────────
        # Strategy 2 → readability
        # ──────────────────────────────────────────────────
        doc = Document(html)
        clean_html = doc.summary()

        soup = BeautifulSoup(clean_html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        if text and len(text.strip()) > 200:
            cleaned = re.sub(r'\s+', ' ', text)
            print(f"  [Tool: scrape_url] Strategy 2 (Readability) succeeded ({len(cleaned)} chars extracted).", flush=True)
            return cleaned[:5000]

        print(f"  [Tool: scrape_url] Strategy 2 yielded insufficient text. Trying Strategy 3 (BS4 fallback)...", flush=True)
        # ──────────────────────────────────────────────────
        # Strategy 3 → fallback full page extraction
        # ──────────────────────────────────────────────────
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        cleaned = re.sub(r'\s+', ' ', text)

        if cleaned:
            print(f"  [Tool: scrape_url] Strategy 3 (BS4 full-page fallback) succeeded ({len(cleaned)} chars extracted).", flush=True)
            return cleaned[:5000]

        print(f"  [Tool: scrape_url] Warning: Could not extract meaningful content from {url}", flush=True)
        return "Could not extract meaningful content from the page."

    except requests.exceptions.Timeout:
        print(f"  [Tool: scrape_url] Timeout: Request timed out after 15s for {url}", flush=True)
        return "Request timed out while scraping the URL."

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        print(f"  [Tool: scrape_url] HTTP {status_code} Error: {e}", flush=True)
        return f"HTTP error occurred: {str(e)}"

    except Exception as e:
        print(f"  [Tool: scrape_url] Scraping Error: {e}", flush=True)
        return f"Could not scrape URL: {str(e)}"
