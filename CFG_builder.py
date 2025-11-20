#!/usr/bin/env python
# @Name: CFG_builder.py
# @Project: librefuzz
# @Author: Tristan Stapert
# @Created: 11/17/25

import os
import json
import logging
import string


def initialize_amalgamation():
    cfg_json = {
        "START": ["STMT"],
        "STMT": [],
        "D_QUOTE": ['"'],
        "SEP": ["';'"],
        "NEG": ["'-'"],
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
            "'9960'",
            "FUZZNUMBER",
            "NEG NUMBER",
        ],
        "FUZZNUMBER": [
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
            "'9999999999999999999'",  # big number lol
            "'-9999999999999999999'",  # small number lol
        ],
        "COMPLEX_N": ["D_QUOTE NUMBER OPERATOR NUMBER 'i' D_QUOTE", "D_QUOTE NUMBER OPERATOR NUMBER 'j' D_QUOTE"],
        "TEXT": ["LETTER", "TEXT LETTER"],
        "LETTER": [f"'{letter}'" for letter in string.printable],
        "CELL": ["LETTER NUMBER", "LETTER LETTER NUMBER", "LETTER LETTER LETTER NUMBER"],
        "CELL_RANGE": ["CELL ':' CELL"],
    }
    return cfg_json


amalgamation = initialize_amalgamation()

print(json.dumps(amalgamation, indent=4))
