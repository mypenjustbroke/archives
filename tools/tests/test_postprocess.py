import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
import postprocess


def soup_from(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_strip_edit_links_removes_action_edit_anchors():
    html = '''
    <ul>
      <li id="ca-edit"><a href="/wiki/Foo?action=edit"><span>Edit</span></a></li>
      <li id="ca-ve-edit"><a href="/wiki/Foo?veaction=edit"><span>Edit</span></a></li>
      <li id="ca-view"><a href="/wiki/Foo">Read</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_edit_links(soup)
    assert soup.find(id="ca-edit") is None
    assert soup.find(id="ca-ve-edit") is None
    assert soup.find(id="ca-view") is not None


def test_strip_edit_links_removes_section_edit_brackets():
    html = '''
    <h2>
      <span class="mw-headline" id="Section">Section</span>
      <span class="mw-editsection">
        <span class="mw-editsection-bracket">[</span>
        <a href="/wiki/Foo?action=edit&section=1">edit</a>
        <span class="mw-editsection-bracket">]</span>
      </span>
    </h2>
    '''
    soup = soup_from(html)
    postprocess.strip_edit_links(soup)
    assert soup.find(class_="mw-editsection") is None
    assert soup.find(class_="mw-headline") is not None


def test_strip_history_and_action_tabs_removes_known_ids():
    html = '''
    <ul>
      <li id="ca-history"><a>History</a></li>
      <li id="ca-watch"><a>Watch</a></li>
      <li id="ca-unwatch"><a>Unwatch</a></li>
      <li id="ca-move"><a>Move</a></li>
      <li id="ca-delete"><a>Delete</a></li>
      <li id="ca-protect"><a>Protect</a></li>
      <li id="ca-purge"><a>Purge</a></li>
      <li id="ca-view"><a>Read</a></li>
      <li id="ca-talk"><a>Talk</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_history_and_action_tabs(soup)
    for stripped in ("ca-history", "ca-watch", "ca-unwatch", "ca-move",
                     "ca-delete", "ca-protect", "ca-purge"):
        assert soup.find(id=stripped) is None, f"{stripped} should be removed"
    assert soup.find(id="ca-view") is not None
    assert soup.find(id="ca-talk") is not None


def test_strip_login_and_account_links_removes_personal_tools():
    html = '''
    <ul id="p-personal-tools">
      <li id="pt-anonuserpage">Not logged in</li>
      <li id="pt-anontalk"><a>Talk for this IP</a></li>
      <li id="pt-anoncontribs"><a>Contributions</a></li>
      <li id="pt-createaccount"><a>Create account</a></li>
      <li id="pt-login"><a>Log in</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_login_and_account_links(soup)
    for stripped in ("pt-anonuserpage", "pt-anontalk", "pt-anoncontribs",
                     "pt-createaccount", "pt-login"):
        assert soup.find(id=stripped) is None, f"{stripped} should be removed"


def test_strip_special_recentchanges_link_removes_sidebar_entry():
    html = '''
    <ul>
      <li id="n-mainpage-description"><a href="/wiki/Main_Page">Main page</a></li>
      <li id="n-recentchanges"><a href="/wiki/Special:RecentChanges">Recent changes</a></li>
      <li id="n-randompage"><a href="/wiki/Special:Random">Random</a></li>
      <li id="n-help-mediawiki"><a href="https://www.mediawiki.org/">Help</a></li>
    </ul>
    '''
    soup = soup_from(html)
    postprocess.strip_special_recentchanges_link(soup)
    assert soup.find(id="n-recentchanges") is None
    assert soup.find(id="n-help-mediawiki") is None
    assert soup.find(id="n-mainpage-description") is not None
    assert soup.find(id="n-randompage") is None


def test_inject_site_notice_adds_banner_at_top_of_content():
    html = '''
    <html><body>
      <div id="content" class="mw-body" role="main">
        <h1 id="firstHeading">Foo</h1>
        <div id="bodyContent">...</div>
      </div>
    </body></html>
    '''
    soup = soup_from(html)
    postprocess.inject_site_notice(soup)
    notice = soup.find(id="archives-notice")
    assert notice is not None, "site notice div not injected"
    assert "snapshot" in notice.get_text().lower()
    h1 = soup.find(id="firstHeading")
    siblings_before_h1 = []
    for sib in h1.previous_siblings:
        if hasattr(sib, "get") and sib.get("id"):
            siblings_before_h1.append(sib.get("id"))
    assert "archives-notice" in siblings_before_h1


def test_inject_site_notice_idempotent():
    html = '<div id="content"><h1 id="firstHeading">X</h1></div>'
    soup = soup_from(html)
    postprocess.inject_site_notice(soup)
    postprocess.inject_site_notice(soup)
    assert len(soup.find_all(id="archives-notice")) == 1


def test_swap_search_box_for_pagefind_replaces_native_form():
    html = '''
    <html><head></head><body>
      <form action="/wiki/Special:Search" id="searchform">
        <input id="searchInput" type="search" name="search">
        <input type="submit" name="go" value="Go">
      </form>
    </body></html>
    '''
    soup = soup_from(html)
    postprocess.swap_search_box_for_pagefind(soup)
    assert soup.find(id="searchform") is None
    assert soup.find(id="archives-search") is not None
    head = soup.find("head")
    css = head.find("link", href=lambda h: h and "/pagefind/pagefind-ui.css" in h)
    js = head.find("script", src=lambda s: s and "/pagefind/pagefind-ui.js" in s)
    assert css is not None
    assert js is not None


def test_neutralize_localhost_links_relativizes_wiki_urls():
    html = '''
    <a id="cat" href="http://localhost:8080/wiki/Category:Legislation">Cat</a>
    <a id="art" href="http://localhost:8080/wiki/Foo_Act">Foo</a>
    '''
    soup = soup_from(html)
    postprocess.neutralize_localhost_links(soup)
    assert soup.find(id="cat")["href"] == "/wiki/Category:Legislation"
    assert soup.find(id="art")["href"] == "/wiki/Foo_Act"


def test_neutralize_localhost_links_strips_dynamic_endpoint_hrefs():
    html = '''
    <a id="edit" class="new" href="http://localhost:8080/index.php?title=Foo&amp;action=edit&amp;redlink=1">Foo</a>
    <a id="api" href="http://localhost:8080/api.php?action=rsd">api</a>
    <a id="rest" href="http://localhost:8080/rest.php/v1/search">rest</a>
    <a id="hist" href="http://localhost:8080/index.php?title=Foo&amp;oldid=42">old</a>
    '''
    soup = soup_from(html)
    postprocess.neutralize_localhost_links(soup)
    for stripped_id in ("edit", "api", "rest", "hist"):
        a = soup.find(id=stripped_id)
        assert a is not None, f"{stripped_id} anchor should be preserved"
        assert "href" not in a.attrs, f"{stripped_id} should have no href"
        # Visible text preserved
        assert a.get_text().strip() != ""


def test_neutralize_localhost_links_strips_form_action():
    html = '<form id="f" action="http://localhost:8080/index.php"><input/></form>'
    soup = soup_from(html)
    postprocess.neutralize_localhost_links(soup)
    assert "action" not in soup.find(id="f").attrs


def test_neutralize_localhost_links_leaves_external_and_relative_alone():
    html = '''
    <a id="ext" href="https://example.com/foo">ext</a>
    <a id="rel" href="/wiki/Bar">rel</a>
    '''
    soup = soup_from(html)
    postprocess.neutralize_localhost_links(soup)
    assert soup.find(id="ext")["href"] == "https://example.com/foo"
    assert soup.find(id="rel")["href"] == "/wiki/Bar"


def test_inject_favicon_adds_link_in_head():
    html = '<html><head><title>X</title></head><body></body></html>'
    soup = soup_from(html)
    postprocess.inject_favicon(soup)
    icon = soup.find("link", rel="icon")
    assert icon is not None
    assert icon["href"] == "/favicon.png"
    assert icon.get("type") == "image/png"


def test_inject_favicon_idempotent():
    html = '<html><head><title>X</title></head></html>'
    soup = soup_from(html)
    postprocess.inject_favicon(soup)
    postprocess.inject_favicon(soup)
    assert len(soup.find_all("link", rel="icon")) == 1


def test_inject_logo_override_adds_css_rule_targeting_mw_wiki_logo():
    html = '<html><head><title>X</title></head></html>'
    soup = soup_from(html)
    postprocess.inject_logo_override(soup)
    style = soup.find("style", id="archives-logo-override")
    assert style is not None
    rendered = str(style)
    assert ".mw-wiki-logo" in rendered
    assert "/assets/logo.jpg" in rendered


def test_inject_logo_override_idempotent():
    html = '<html><head></head></html>'
    soup = soup_from(html)
    postprocess.inject_logo_override(soup)
    postprocess.inject_logo_override(soup)
    assert len(soup.find_all("style", id="archives-logo-override")) == 1


def test_strip_printfooter_removes_retrieved_from_div():
    html = '''
    <div id="content">
      <div class="printfooter" data-nosnippet="">Retrieved from "<a dir="ltr">http://localhost:8080/index.php?title=Foo&amp;oldid=42</a>"</div>
    </div>
    '''
    soup = soup_from(html)
    postprocess.strip_printfooter(soup)
    assert soup.find(class_="printfooter") is None


def test_neutralize_localhost_links_drops_link_tags_pointing_at_localhost():
    html = '''
    <html><head>
      <link rel="search" type="application/opensearchdescription+xml"
            href="http://localhost:8080/rest.php/v1/search"/>
      <link rel="EditURI" type="application/rsd+xml"
            href="http://localhost:8080/api.php?action=rsd"/>
      <link rel="alternate" type="application/atom+xml"
            href="http://localhost:8080/index.php?title=Special:RecentChanges&amp;feed=atom"/>
      <link rel="stylesheet" href="/pagefind/pagefind-ui.css"/>
      <link rel="canonical" href="https://archives.mypenjustbroke.com/wiki/Foo"/>
    </head></html>
    '''
    soup = soup_from(html)
    postprocess.neutralize_localhost_links(soup)
    head = soup.find("head")
    # All localhost-bearing link tags removed
    assert head.find("link", attrs={"rel": "search"}) is None
    assert head.find("link", attrs={"rel": "EditURI"}) is None
    assert head.find("link", attrs={"rel": "alternate"}) is None
    # Non-localhost link tags untouched
    assert head.find("link", attrs={"rel": "stylesheet"}) is not None
    assert head.find("link", attrs={"rel": "canonical"}) is not None
