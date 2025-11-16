#!/usr/bin/env python
# @Name: function_def_scraper.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025

import os  # Handle filesystem operations
import time  # Delay requests as not to spam website
import logging  # Handle log level output

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
"""
targets = [
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060107.html?DbPAR=CALC",  # array
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060120.html?DbPAR=CALC",  # bitwise
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060101.html?DbPAR=CALC",  # database
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
    "https://help.libreoffice.org/latest/en-US/text/scalc/01/04060199.html?DbPAR=CALC",  # operators (Needs better scraping)
]

labels = [
    "array",
    "bitwise",
    "database",
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
    "spreadsheeet",
    "text",
    "operator",
]
logger.info("Targets and labels defined.")

"""
Make nice pairs of labels and target URLs for easier processing later
"""
labeled_targets = list(zip(labels, targets))
logger.info("Labeled target pairs created.")

"""
Collect a copy of all pages to scrape 
"""
logger.info("Webscrape begin:")
pages = []
for pair in labeled_targets:
    label = pair[0]
    target = pair[1]
    if os.path.isfile(f"page_scrapes/{label}.html"):
        logger.info(f"Page {label} already scraped.")
        continue
    else:
        logger.info(f"Page {label} now scraping.")
        time.sleep(1)
        try:
            pages.append((label, requests.get(target)))
        except Exception as e:
            logger.error(f"Page {label} failed with exception {e}")

"""
To minimize requests to websites, we will cache pages locally to do further parsing pipelines.
"""
if len(pages) > 0:
    try:
        logger.info(f"Trying to make 'page_scrapes' directory.")
        os.mkdir("page_scrapes")
    except FileExistsError:
        logger.warning(f"'page_scrapes' directory already exists.")

    for o in pages:
        label = o[0]
        page = o[1]
        logger.info(f"Now writing: {label}.html")
        with open(f"page_scrapes/{label}.html", "wb") as f:
            f.write(page.content)
else:
    logger.info("No pages scraped.")

# TODO Refactor this to have function breakouts for copied code
"""
DATETIME
Add additional targets since Date + Time has breakouts to new pages
Does effectively the same steps as above but needs data cleaning and acquisition from the datetime page previously collected
"""
url_preface = "https://help.libreoffice.org/latest/"
dt_targets = []
with open("page_scrapes/datetime.html", "r") as f:
    logger.info("Beginning date time scraping.")
    dt_soup = BeautifulSoup(f.read(), "html.parser")
    hrefs = [tag["href"] for tag in dt_soup.find_all("a", href=True)]  # Find all sublinks within the document
    for href in hrefs[2:-10]:  # Clean down to the function sublinks
        dt_targets.append(f"{url_preface}{href}")  # Build new targets with full URLs

logger.info("New targets added.")
labels = [
    label.split("/")[-1].split(".")[0]  # Each label starts as a relative URL. This cleans down to the filename
    for label in dt_targets
]

# Reset the existing stores
labeled_targets = list(zip(labels, dt_targets))  # Pair labels and targets
pages.clear()
for pair in labeled_targets:
    label = pair[0]
    target = pair[1]
    if os.path.isfile(f"page_scrapes/datetime/{label}.html"):
        logger.info(f"Page {label} already scraped.")
        continue
    else:
        logger.info(f"Page {label} now scraping.")
        time.sleep(1)
        try:
            pages.append((label, requests.get(target)))
        except Exception as e:
            logger.error(f"Page {label} failed with exception {e}")


if len(pages) > 0:
    try:
        logger.info(f"Trying to make 'datetime' directory.")
        os.mkdir("page_scrapes/datetime/")
    except FileExistsError:
        logger.warning(f"'page_scrapes' directory already exists.")

    for o in pages:
        label = o[0]
        page = o[1]
        logger.info(f"Now writing: {label}.html")
        with open(f"page_scrapes/datetime/{label}.html", "wb") as f:
            f.write(page.content)
else:
    logger.info("No pages scraped.")

"""
TEXT
Add additional targets since text has breakouts to new pages
Does effectively the same steps as above but needs data cleaning and acquisition from the datetime page previously collected
"""
t_targets = []
with open("page_scrapes/text.html", "r") as f:
    logger.info("Beginning text scraping.")
    t_soup = BeautifulSoup(f.read(), "html.parser")
    hrefs = [tag["href"] for tag in t_soup.find_all("a", href=True)]  # Find all sublinks within the document
    for href in hrefs[2:-10]:  # Clean down to the function sublinks
        t_targets.append(f"{url_preface}{href}")  # Build new targets with full URLs

logger.info("New targets added.")
labels = [
    label.split("/")[-1].split(".")[0]  # Each label starts as a relative URL. This cleans down to the filename
    for label in t_targets
]

# Reset the existing stores
labeled_targets = list(zip(labels, t_targets))  # Pair labels and targets
pages.clear()
for pair in labeled_targets:
    label = pair[0]
    target = pair[1]
    if os.path.isfile(f"page_scrapes/datetime/{label}.html"):
        logger.info(f"Page {label} already scraped.")
        continue
    else:
        logger.info(f"Page {label} now scraping.")
        time.sleep(1)
        try:
            pages.append((label, requests.get(target)))
        except Exception as e:
            logger.error(f"Page {label} failed with exception {e}")

# TODO refactor this to elimate the separate caching step
if len(pages) > 0:
    try:
        logger.info(f"Trying to make 'datetime' directory.")
        os.mkdir("page_scrapes/text/")
    except FileExistsError:
        logger.warning(f"'page_scrapes' directory already exists.")

    for o in pages:
        label = o[0]
        page = o[1]
        logger.info(f"Now writing: {label}.html")
        with open(f"page_scrapes/text/{label}.html", "wb") as f:
            f.write(page.content)
else:
    logger.info("No pages scraped.")

logger.info("FINISHED")
