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
