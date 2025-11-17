#!/usr/bin/env python
# @Name: grammar_builder.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025

import os
from collections import deque
from bs4 import BeautifulSoup


def cleaner(value):
    old = value.text.strip()
    new = old if old != "" else None
    return new


fullpath = os.path.abspath("page_scrapes")
to_check = deque()
to_check.append(fullpath)
while len(to_check) > 0:
    for root, dirs, files in os.walk(to_check.popleft()):
        for dir in dirs:
            to_check.append(os.path.join(root, dir))
        for file in files:
            if file.endswith(".html"):
                with open(os.path.join(root, file), "r") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    results = soup.find_all("p", {"class": "code"})
                    in_between_results = list(map(cleaner, results))
                    clean_results = [i for i in in_between_results if i is not None]
                    if len(clean_results) > 0:
                        with open(f"{os.path.join(root, file)}.txt", "w") as outfile:
                            for result in clean_results:
                                print(result)
                                outfile.write(result)
                                outfile.write("\n")
                    else:
                        results = soup.select("span[data-tooltip]")
                        if file in [
                            "func_unicode.html",
                            "func_unichar.html",
                        ]:  # Edge case where span is class "literal"
                            results.clear()
                            spans = soup.find_all("span")
                            for span in spans:
                                if span["class"] == ["literal"]:
                                    results.append(span)
                        elif file == "operator.html":  # Edge case where data is in tables
                            results.clear()
                            rows = soup.find_all("tr")
                            for row in rows[:-10]:
                                cells = row.find_all("td")
                                if cells:
                                    results.append(cells[0].get_text(strip=True))
                            with open(f"{os.path.join(root, file)}.txt", "w") as outfile:
                                for result in results:
                                    print(result)
                                    outfile.write(result)
                                    outfile.write("\n")
                            continue
                        if len(results) > 0:
                            print(results[0].text)
                            with open(f"{os.path.join(root, file)}.txt", "w") as outfile:
                                outfile.write(results[0].text)
                                outfile.write("\n")
