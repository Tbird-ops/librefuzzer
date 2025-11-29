#!/usr/bin/env python
# @Name: CFG_builder.py
# @Project: librefuzz
# @Author: Tristan Stapert
# @Created: 11/17/25

import os
import json
import re
from collections import deque
import logging
import string

# Easier logging control for tracking program status
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("INITIALIZED CFG_BUILDER.PY")


def initialize_amalgamation() -> dict:
    """
    Hand crafted language to then use along programmatic function extraction
    :return: a dictionary collection of grammar keys to possible values it can expand to.

    !!! AI DISCLOSURE (ONLY WITHIN THIS FUNCTION)!!!
    Grammar analysis performed by Claude Code Pro Sonnet 4.5 model
    Claude was used to analyze all LibreOffice Calc source and identify some acceptable grammar components for expressions
    The remapping here was discovered by Claude Code's analysis, then was validated, edited, and made into a function by Tristan
    """
    cfg_json = {
        "START": ["FORMULA"],
        "FORMULA": ["'=' EXPRESSION"],
        "EXPRESSION": ["COMPARE_EXPR"],
        "COMPARE_EXPR": ["ARITH_EXPR", "ARITH_EXPR COMPARE_OP ARITH_EXPR"],
        "ARITH_EXPR": ["FACTOR", "FACTOR ARITH_OP FACTOR"],
        "FACTOR": ["LITERAL", "REFERENCE", "FUNCTION_CALL", "FUNC_BEG EXPRESSION FUNC_END"],
        "LITERAL": ["NUMBER", "TEXT", "DATE"],
        "REFERENCE": ["CELL", "CELL ':' CELL"],
        "FUNCTION_CALL": [],
        "ARG_RECUR": ["SEP FACTOR", "SEP FACTOR ARG_RECUR"],
        "DASH": ["'-'"],  # Works as negative, arithmetic minus, and date separator
        "SEP": ["';'"],
        "FUNC_BEG": ["'('"],
        "FUNC_END": ["')'"],
        "ABSOLUTE": ["'$'"],
        "ARITH_OP": [
            "'+'",
            "DASH",
            "'*'",
            "'/'",
            "'^'",
        ],
        "COMPARE_OP": ["'='", "'>'", "'<'", "'>='", "'<='", "'<>'"],
        "NUMBER": [
            "'1'",
            "'2'",
            "'3'",
            "'4'",
            "'5'",
            "'6'",
            "'7'",
            "'8'",
            "'9'",
            "'10'",  # ^ Bounds of most "mode" type parameters are <10
            "'11'",
            "'12'",  # Edge of months
            "'13'",
            "'14'",
            "'27'",
            "'28'",
            "'29'",
            "'30'",
            "'31'",
            "'32'",
            "'33'",
            "'98'",
            "'99'",  # High edge of short year
            "'100'",
            "'101'",
            "'1580'",
            "'1581'",
            "'1582'",
            "'1583'",  # Low edge of years
            "'1584'",
            "'9956'",
            "'9957'",  # High edge of years
            "'9958'",
            "'9959'",
            "'9960'",  # Below are fuzzing numbers
            "'0'",  # Zeros
            "'0.0'",  # float zero
            "'-0'",  # negative 0
            "'-1'",  # Negative 1
            "'-1.0'",  # Negative 1 float
            "'-128'",  # i8 min
            "'-129'",  # underflow?
            "'127'",  # i8 max
            "'128'",  # overflow?
            "'255'",  # u8 max
            "'256'",  # overflow?
            "'65535'",  # u16 max
            "'65536'",  # overflow?
            "'-32768'",  # i16 min
            "'-32769'",  # underflow
            "'32767'",  # i16 max
            "'32768'",  # overflow
            "'2147483647'",  # i32 max
            "'2147483648'",  # overflow
            "'-2147483648'",  # i32 min
            "'-2147483649'",  # underflow
            "'-2147483648/-1'",  # i32 min / neg 1 = overflow
            "'4294967295'",  # u32 max
            "'4294967296'",  # overflow
            "'999999999999999999999'",  # big number lol
            "'-999999999999999999999'",  # small number lol
            "DASH NUMBER",
        ],
        "TEXT": ["LETTER", "LETTER TEXT"],
        "LETTER": [f"'{letter}'" for letter in string.ascii_uppercase],
        "CELL": [
            "LETTER NUMBER",
            "ABSOLUTE LETTER ABSOLUTE NUMBER",
            "ABSOLUTE LETTER NUMBER",
            "LETTER ABSOLUTE NUMBER",
            "'A1'",
            "'B1'",
            "'C1'",
        ],
        "DATE": ["NUMBER DASH NUMBER DASH NUMBER"],
    }
    return cfg_json


# For each function
# First parameter: "FACTOR"
# Next parameters: "SEP FACTOR"
# Optional parameters: provide variation with either "SEP FACTOR" or "SEP" dictating filled or empty
# IF recursive: provide variation with either "FACTOR" or "FACTOR ARG_RECUR"
def parse_function(line: str) -> list:
    """
    Parse each provided function and create a CFG language ready value
    :param line: extracted function definition from the grammar_extractor functions.
    :return: a list of all possible variations for use in the grammar (optionals set or unset, etc)
    """
    variations = []
    match = re.match(r"^(.+)\s*\((.*)\)", line)
    function_name = match.group(1)
    try:
        parameters = match.group(2).split(";")
        if " N: " in parameters[0]:
            variations.append(f"'{function_name}' FUNC_BEG FACTOR ")
            variations.append(f"'{function_name}' FUNC_BEG FACTOR ARG_RECUR ")
        else:
            for i in range(len(parameters)):
                if i == 0:
                    variations.append(f"'{function_name}' FUNC_BEG FACTOR ")
                elif "[" in parameters[i]:
                    for term in range(len(variations)):
                        variations.append(variations[term])
                    for term in range(len(variations)):
                        if term < len(variations) / 2:
                            variations[term] += "SEP FACTOR "
                        else:
                            variations[term] += "SEP "
                else:
                    for term in range(len(variations)):
                        variations[term] += "SEP FACTOR "

    except IndexError as e:
        logger.warning(f"{function_name} has no parameters")
    finally:
        for term in range(len(variations)):
            variations[term] += "FUNC_END"
        return variations


# For now, ignore my type system and just mark parameters as expressions. We will see if types are needed
def process_all(base_dir: str) -> list:
    """
    Process all HTML files within the provided base directory, the end results will be stored in new txt files4
    :param base_dir: str with the base directory to begin processing
    :return: List of function_calls in CFG format to be inserted to amalgamation"""
    to_check = deque()  # Store additional directories to parse files from
    to_check.append(base_dir)  # Prime queue with first directory
    function_calls = []  # Store all variations of function calls determined from parsing.
    while len(to_check) > 0:  # While there are still directories to parse
        for root, dirs, files in os.walk(to_check.popleft()):  # Read all directory contents
            for d in dirs:  # Add each new directory to queue
                to_check.append(os.path.join(root, d))
            for file in files:  # Parse each discovered file
                if file.endswith(".txt"):  # Only use the "TXT" files
                    logger.info("Now processing file: " + file)  # Then process the file as normal
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        for line in f.readlines():
                            function_variations = parse_function(line)
                            function_calls += function_variations
    return function_calls


amalgamation = initialize_amalgamation()
amalgamation["FUNCTION_CALL"] = process_all("page_scrapes")
with open("amalgamation.json", "w", encoding="utf-8") as f:
    json.dump(amalgamation, f, ensure_ascii=False, indent=4)

logger.info("FINISHED CFG BUILD PROC")