#!/usr/bin/env python
# @Name: function_def_scraper.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025

import os  # Handle filesystem operations
import time  # Delay requests as not to spam website
import logging  # Handle log level output
import random as rand  # Handle random number creation

# Easier logging control for tracking program status
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("INITIALIZED")

import requests  # Perform the web requests
from bs4 import BeautifulSoup  # Help parse and further control

"""
Targets to fetch from the pages connecting from this one: https://help.libreoffice.org/latest/en-US/text/scalc/01/04060000.html?DbPAR=CALC
These are the online documentation outlines of the syntactical requirements of certain formula functions
Some outlier pages exist on the following:
- Date + Time: Does not provide definitions in page, but links to subpages for all commands with a definition
- Text: Some commands are sublinked on the page, and a few comparison commands are listed differently.
- Addin3: There are several commands sublinked, but most are defined in page

The following pages are omitted due to more complex requirements for cell types. Hopefully will add these later:
- Array: Special cell range linking to perform group operations
- Database: Rectangular cell range defining simple database with first row indicating features, 
            and subsequent rows providing instance data
- 
"""
base_targets = [
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060120.html?DbPAR=CALC",  # bitwise
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060102.html?DbPAR=CALC",  # date + time  (Contains sublinks to more defs)
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060103.html?DbPAR=CALC",  # finance pt 1
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060119.html?DbPAR=CALC",  # finance pt 2
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060118.html?DbPAR=CALC",  # finance pt 3
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060104.html?DbPAR=CALC",  # information functions
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060105.html?DbPAR=CALC",  # logical
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060106.html?DbPAR=CALC",  # mathematical
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060181.html?DbPAR=CALC",  # Stats pt 1
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060182.html?DbPAR=CALC",  # stats pt 2
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060183.html?DbPAR=CALC",  # stats pt 3
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060184.html?DbPAR=CALC",  # stats pt 4
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060185.html?DbPAR=CALC",  # stats pt 5
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060109.html?DbPAR=CALC",  # spreadsheet
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060110.html?DbPAR=CALC",  # text     (Contains sublinks to defs)
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060199.html?DbPAR=CALC",  # operators (Needs better scraping or by hand. Not many items)
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060111.html?DbPAR=CALC",  # Add-ins pt 1
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060115.html?DbPAR=CALC",  # Add-ins pt 2
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060116.html?DbPAR=CALC",  # Add-ins pt 3 (Has both definitions and sublinks)
]

base_labels = [
    "bitwise",
    "datetime",
    "finance1",
    "finance2",
    "finance3",
    "info",
    "logical",
    "math",
    "stat1",
    "stat2",
    "stat3",
    "stat4",
    "stat5",
    "spreadsheet",
    "text",
    "operator",
    "addin1",
    "addin2",
    "addin3",
]
url_preface = "https://help.libreoffice.org/latest/"
logger.info("Initial targets and labels defined.")


def jitter() -> float:
    """Produce a random float value between 0-5 to wait between fetching a page"""
    tmp = float(rand.randint(1, 5))
    offset = 1.0 / float(rand.randint(1, 10))
    tmp = tmp - offset
    return float(tmp)


def scraper_cacher(labeled_targets: list[tuple], directory: str = None):
    """Collect a copy of all scraped pages"""
    logger.info("Webscrape begin:")

    # Set the subdirectory to store page cache
    subdir = directory if directory is not None else ""
    if not os.path.exists(f"page_scrapes/{subdir}"):
        logger.info(f"Making 'page_scrapes' directory.")
        os.mkdir(f"page_scrapes/{subdir}")

    for pair in labeled_targets:
        label = pair[0]
        target = pair[1]

        # Empty edgecases produced in adding additional TEXT sublinks
        if label in ["01140000", "00000005", "04060110"]:
            continue

        # Check if page is cached before trying to scrape it
        if os.path.isfile(f"page_scrapes/{subdir}/{label}.html"):
            logger.info(f"Page {label} already scraped.")
            continue
        else:
            logger.info(f"Page {label} now scraping.")
            time.sleep(jitter())
            page = requests.get(target)
            if page.status_code == 200:
                logger.info(f"Now writing: {label}.html")
                filename = f"page_scrapes/{label}.html" if directory is None else f"page_scrapes/{directory}/{label}.html"
                with open(filename, "wb") as f:
                    f.write(page.content)
            else:
                logger.warn(f"Page {label} not scraped.")


def extractor(html_file: str, start: int, stop: int) -> list[str]:
    """Used to extract page sublinks needed to find additional grammar definitions"""
    with open(html_file, "r") as f:
        logger.info(f"Beginning to parse {html_file}")
        f_soup = BeautifulSoup(f.read(), "html.parser")
        hrefs = [tag["href"] for tag in f_soup.find_all("a", href=True)]
        ret_targets = [f"{url_preface}{href}" for href in hrefs[start:stop]]
        return ret_targets


def labeler(labels: list[str], targets: list[str]) -> list[tuple]:
    """Make nice pairs of labels and target URLs for easier processing later"""
    lt = list(zip(labels, targets))
    logger.info("Labeled target pairs created.")
    return lt


def label_maker(unlabeled_targets: list[str]) -> list[str]:
    """Takes a list of URL targets, and makes a label list based on the HTML file in the path"""
    return [label.split("/")[-1].split(".")[0] for label in unlabeled_targets]


"""
MAIN SCRAPE
"""
if __name__ == "__main__":
    scraper_cacher(labeler(base_labels, base_targets))

    """
    DATETIME
    Add additional targets since Date + Time has breakouts to new pages
    Does effectively the same steps as above but needs data cleaning and acquisition from the datetime page previously collected
    PATH: "page_scrapes/datetime.html"
    START: 2
    STOP: -10
    DIRECTORY: "datetime"
    """
    dt_targets = extractor("page_scrapes/datetime.html", 2, -10)  # First 2 dead, last 10 dead
    scraper_cacher(labeler(label_maker(dt_targets), dt_targets), "datetime")

    """
    TEXT
    Add additional targets since text has breakouts to new pages
    Does effectively the same steps as above but needs data cleaning and acquisition from the datetime page previously collected
    PATH: "page_scrapes/text.html"
    START: 2
    STOP: -10
    DIRECTORY: "text"
    """
    t_targets = extractor("page_scrapes/text.html", 2, -10)  # First 2 dead, last 10 dead
    scraper_cacher(labeler(label_maker(t_targets), t_targets), "text")

    """
    ADDINS3
    Add additional targets since there are some breakout pages
    PATH: "page_scrapes/addins3.html"
    START: 3
    STOP: -13
    DIRECTORY: "addins3"
    """
    a_targets = extractor("page_scrapes/addin3.html", 3, -13)  # First 3 dead, last 13 dead
    scraper_cacher(labeler(label_maker(a_targets), a_targets), "addin3")

    logger.info("FINISHED")
