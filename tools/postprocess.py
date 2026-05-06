"""HTML mutation pipeline applied to wget-mirrored MediaWiki output."""
from __future__ import annotations
from bs4 import BeautifulSoup


def transform(html: str) -> str:
    """Apply all mutations and return the modified HTML string."""
    soup = BeautifulSoup(html, "lxml")
    strip_edit_links(soup)
    strip_history_and_action_tabs(soup)
    strip_login_and_account_links(soup)
    strip_special_recentchanges_link(soup)
    strip_printfooter(soup)
    neutralize_localhost_links(soup)
    inject_site_notice(soup)
    swap_search_box_for_pagefind(soup)
    return str(soup)


def strip_printfooter(soup: BeautifulSoup) -> None:
    """Remove the 'Retrieved from "<url>"' attribution that MediaWiki
    emits at the bottom of every page. The URL is the localhost build
    server (e.g. http://localhost:8080/index.php?...), which is meaningless
    and ugly on a static archive."""
    for el in soup.find_all(class_="printfooter"):
        el.decompose()


def neutralize_localhost_links(soup: BeautifulSoup) -> None:
    """Strip http://localhost:8080 prefix from /wiki/... refs (real content
    we mirrored), and remove href/action attributes entirely from anything
    else pointing at localhost (dynamic endpoints — edit, api, rest, oldid,
    Special:WhatLinksHere — which don't exist on the static mirror).
    Also delete <link> tags in <head> whose href points at localhost
    (atom feeds, OpenSearch description, RSD — all dynamic endpoints
    not available on a static archive)."""
    LOCAL = "http://localhost:8080"
    for tag in soup.find_all(["a", "form"]):
        for attr in ("href", "action"):
            url = tag.get(attr)
            if not url or not url.startswith(LOCAL):
                continue
            path = url[len(LOCAL):]
            if path.startswith("/wiki/"):
                tag[attr] = path
            else:
                del tag[attr]
    for link in soup.find_all("link"):
        href = link.get("href", "")
        if href.startswith(LOCAL):
            link.decompose()


def strip_edit_links(soup: BeautifulSoup) -> None:
    for li_id in ("ca-edit", "ca-ve-edit"):
        for el in soup.find_all(id=li_id):
            el.decompose()
    for el in soup.find_all(class_="mw-editsection"):
        el.decompose()


def strip_history_and_action_tabs(soup: BeautifulSoup) -> None:
    for li_id in ("ca-history", "ca-watch", "ca-unwatch", "ca-move",
                  "ca-delete", "ca-protect", "ca-purge"):
        for el in soup.find_all(id=li_id):
            el.decompose()


def strip_login_and_account_links(soup: BeautifulSoup) -> None:
    for li_id in ("pt-anonuserpage", "pt-anontalk", "pt-anoncontribs",
                  "pt-createaccount", "pt-login", "pt-userpage", "pt-mytalk",
                  "pt-preferences", "pt-watchlist", "pt-mycontris",
                  "pt-logout"):
        for el in soup.find_all(id=li_id):
            el.decompose()


def strip_special_recentchanges_link(soup: BeautifulSoup) -> None:
    for li_id in ("n-recentchanges", "n-help-mediawiki", "n-randompage",
                  "n-portal", "n-currentevents"):
        for el in soup.find_all(id=li_id):
            el.decompose()


SITE_NOTICE_HTML = (
    '<div id="archives-notice" '
    'style="background:#fff8dc;border:1px solid #d4c876;'
    'padding:8px 12px;margin:0 0 12px 0;font-size:90%;border-radius:3px;">'
    'Frozen snapshot of the SimDemocracy Archives, captured 2026-05-05. '
    'Read-only mirror; no edit, no live updates. '
    '<a href="https://mypenjustbroke.com">mypenjustbroke.com</a>'
    '</div>'
)


def inject_site_notice(soup: BeautifulSoup) -> None:
    if soup.find(id="archives-notice"):
        return
    h1 = soup.find(id="firstHeading")
    if h1 is None:
        return
    notice = BeautifulSoup(SITE_NOTICE_HTML, "lxml").find(id="archives-notice")
    h1.insert_before(notice)


PAGEFIND_PLACEHOLDER_HTML = (
    '<div id="archives-search" style="margin:6px 0;"></div>'
)
PAGEFIND_INIT_SCRIPT = (
    '<script>'
    'window.addEventListener("DOMContentLoaded",function(){'
    'new PagefindUI({element:"#archives-search",showSubResults:true});'
    '});'
    '</script>'
)


def swap_search_box_for_pagefind(soup: BeautifulSoup) -> None:
    form = soup.find(id="searchform")
    if form is not None:
        placeholder = BeautifulSoup(PAGEFIND_PLACEHOLDER_HTML, "lxml").find(id="archives-search")
        form.replace_with(placeholder)
    head = soup.find("head")
    if head is not None:
        if not head.find("link", href=lambda h: h and "/pagefind/pagefind-ui.css" in h):
            link = soup.new_tag("link", rel="stylesheet", href="/pagefind/pagefind-ui.css")
            head.append(link)
        if not head.find("script", src=lambda s: s and "/pagefind/pagefind-ui.js" in s):
            script = soup.new_tag("script", src="/pagefind/pagefind-ui.js")
            head.append(script)
            init = BeautifulSoup(PAGEFIND_INIT_SCRIPT, "lxml").find("script")
            head.append(init)
