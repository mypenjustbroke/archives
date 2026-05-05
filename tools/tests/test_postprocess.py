import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
import postprocess


def soup_from(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
