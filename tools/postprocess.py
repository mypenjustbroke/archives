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
    raise NotImplementedError("Task 8")


def strip_login_and_account_links(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 9")


def strip_special_recentchanges_link(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 9")


def inject_site_notice(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 10")


def swap_search_box_for_pagefind(soup: BeautifulSoup) -> None:
    raise NotImplementedError("Task 11")
