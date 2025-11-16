#!/usr/bin/env python
# @Name: grammar_builder.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025

import os
from collections import deque
from bs4 import BeautifulSoup


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
                    for result in results:
                        print(result.text)
                    with open(f"{os.path.join(root, file)}.txt", "w") as outfile:
                        for result in results:
                            outfile.write(result.text)
                            outfile.write("\n")
