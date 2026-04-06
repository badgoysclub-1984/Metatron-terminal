#!/usr/bin/env python3
"""
METATRON OS — agents/browser_agent.py
BrowserAgent (charge = 3)
Opens URLs, fetches web content, performs searches.
"""

import webbrowser
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from agents.base_agent import Z9Agent

TIMEOUT = 10
UA = "Mozilla/5.0 (METATRON-OS/1.0; Raspberry Pi 5)"


class BrowserAgent(Z9Agent):
    """Z9 agent with charge 3: web navigation and content retrieval."""

    def __init__(self):
        super().__init__(name="BrowserAgent", charge=3)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": UA})

    def execute(
        self,
        url: str,
        action: str = "open",
        selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Actions:
          open   – open URL in system default browser
          fetch  – HTTP GET + parse HTML, return title + text
          links  – return list of hyperlinks from page
          search – Google search (returns result titles + URLs)
        """
        try:
            if action == "open":
                return self._open(url)
            elif action == "fetch":
                return self._fetch(url, selector)
            elif action == "links":
                return self._links(url)
            elif action == "search":
                return self._google_search(url)   # url used as query string here
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Network unavailable (check Pi connection)"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── private helpers ────────────────────────────────────────

    def _open(self, url: str) -> Dict[str, Any]:
        webbrowser.open(url)
        return {"success": True, "message": f"Opened {url} in browser"}

    def _fetch(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        r = self._session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "No title"
        if selector:
            elements = soup.select(selector)
            text = "\n".join(e.get_text(strip=True) for e in elements)
        else:
            # Remove script/style noise
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        return {
            "success": True,
            "url": url,
            "title": title,
            "text": text[:2000],
            "status_code": r.status_code,
        }

    def _links(self, url: str) -> Dict[str, Any]:
        r = self._session.get(url, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("http"):
                links.append({"text": tag.get_text(strip=True), "url": href})
        return {"success": True, "links": links[:30], "url": url}

    def _google_search(self, query: str) -> Dict[str, Any]:
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        r = self._session.get(search_url, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for g in soup.select("div.g")[:8]:
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("div.VwiC3b")
            results.append({
                "title": title_el.get_text() if title_el else "",
                "url": link_el["href"] if link_el and link_el.has_attr("href") else "",
                "snippet": snippet_el.get_text() if snippet_el else "",
            })
        return {"success": True, "query": query, "results": results}
