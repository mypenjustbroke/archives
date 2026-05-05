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
