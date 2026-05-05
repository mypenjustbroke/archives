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
    inject_site_notice(soup)
    swap_search_box_for_pagefind(soup)
    return str(soup)


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


def swap_search_box_for_pagefind(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 11")
