#!/usr/bin/env python
# @Name: grammar_extractor.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025
# @Version: 0.3

import os
import re
import string
from collections import deque
from bs4 import BeautifulSoup
import logging

# Easier logging control for tracking program status
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("INITIALIZED")


# TODO Clean this up.
# - Duplicate values
# - Diff between number/integer?? Make integers numbers
# - Logical is actually an number
# - String should probably be Text
# - Probably other things
# - Prioritize checks against name of param. If that fails, then check description for keyword map
# - Figure out how to type "Reference" -> edgecase Spreadsheet functions that breaks parser (GOT CUT maybe)
def infer_type(param_name: str, description: str) -> str:
    """
    Infer the specific type of parameter based on its name and description.
    Returns a type annotation string.
    :param param_name: str with the parameter name
    :param description: str with the parameter's description
    :return: type annotation string for a given parameter

    !!! AI DISCLOSURE (ONLY WITHIN THIS FUNCTION)!!!
    Keyword remapping comparison performed by Claude Code Pro Sonnet 4.5 model
    Claude was used to analyze all page scrapes and identify a simplified type mapping for keywords
    The remapping here was discovered by Claude Code's analysis, then was validated, edited, and made into a function by Tristan
    """
    desc_lower = description.lower()
    name_lower = param_name.lower()

    # Date/Time types
    if any(
        word in name_lower for word in ["date", "issue", "settlement", "maturity", "firstinterest", "datepurchased", "firstperiod"]
    ):
        return "Date"

    # Boolean/Logical types
    if "logical" in name_lower or "boolean" in desc_lower or "true or false" in desc_lower:
        return "Boolean"
    if name_lower == "test" and "true or false" in desc_lower:
        return "Boolean"

    # String/Text types
    if any(word in name_lower for word in ["text", "string", "currency", "findtext"]):
        return "String"
    if "text" in desc_lower or "string" in desc_lower or "character" in desc_lower:
        return "String"

    # Integer types
    if "integer" in name_lower or "integer" in desc_lower:
        return "Integer"
    if any(word in name_lower for word in ["count", "frequency", "period", "nper", "npery"]):
        if "integer" in desc_lower or "number of" in desc_lower:
            return "Integer"

    # Numeric types (more general)
    if any(
        word in name_lower
        for word in [
            "number",
            "value",
            "rate",
            "price",
            "cost",
            "salvage",
            "yield",
            "coupon",
            "redemption",
            "investment",
            "discount",
            "nom",
            "nominalrate",
            "base",
            "exponent",
            "dividend",
            "divisor",
            "numerator",
            "denominator",
            "multiple",
            "coefficient",
            "bottom",
            "top",
            "guess",
            "pmt",
            "pv",
            "fv",
            "invest",
            "factor",
        ]
    ):
        return "Number"
    if "number" in desc_lower or "numeric" in desc_lower or "value" in desc_lower:
        return "Number"
    if "percentage" in desc_lower or "percent" in desc_lower:
        return "Number"
    if "coordinate" in desc_lower or "angle" in desc_lower:
        return "Number"

    # Range/Array types
    if "range" in name_lower or "array" in desc_lower or "cell range" in desc_lower:
        return "Range"
    if name_lower in ["values", "coefficients"]:
        return "Range"

    # Position/Index types
    if "position" in name_lower and "position" in desc_lower:
        return "Integer"

    # Function code (special integer)
    if name_lower == "function" and "function code" in desc_lower:
        return "Integer"

    # Basis (typically 0-4 integer)
    if name_lower == "basis":
        return "Integer"

    # Type parameter (integer code)
    if name_lower == "type":
        return "Integer"

    # Month parameter
    if name_lower == "month":
        return "Integer"

    # Life, Period (typically integer in finance functions)
    if name_lower in ["life"]:
        return "Number"

    # Par value (number)
    if name_lower == "par":
        return "Number"

    # Default to generic based on parameter name patterns
    if name_lower.startswith("logical"):
        return "Boolean"

    # If still unknown, return generic
    return "Any"


def type_parameter(param: str, param_description: str) -> str:
    """
    Add inferred typing information to a provided parameter, given its description
    :param param: str with the parameter name
    :param param_description: str with the parameter's description
    :return: str with inferred typing information
    """
    if param.startswith('"') and param.endswith('"'):
        typed = f"{param}: String"
    else:
        param_type = infer_type(param, param_description)
        typed = f"{param}: {param_type}"

    return typed


def create_typed_signature(syntax: str, param_info: dict) -> str:
    """
    Gather information and prepare a function definition for inferred typing
    :param syntax: str with the syntax definition for a single function
    :param param_info: dict with a key, value pairing of param_name: param_description
    :return: str with a syntax complete with inferred types
    """

    # parse signature (Group 1 is the function name, Group 2 is the parameter list)
    match = re.match(r"^=?(.+)\s*\((.*)\)\s*", syntax)
    if not match:
        logger.warning("Syntax not matched: " + syntax)
        return syntax  # When failures occur, just return the existing definition syntax

    func_name = match.group(1).lower()
    params_str = match.group(2).lower().replace("  ", " ")

    # Handle empty parameter list
    if not params_str.strip():
        logger.warning("No params for: " + func_name)
        return syntax  # Same as above, but that some functions don't have parameters. Ex: Datetime NOW() -> current time

    # Split parameters, handle optional nesting
    params = []
    current_param = ""
    bracket_start_depth = 0
    bracket_end_depth = 0
    depth_changed = False

    # Handle recursive case
    recursive = re.match(r"^(\w+)\s+\d+\s*\[;.*", params_str)
    if recursive:
        params.append((f"{recursive.group(1).lower().strip()} N", 0))
    else:
        for char in params_str + ";":
            if char == "[":
                bracket_end_depth += 1
                depth_changed = True
            elif char == "]":
                bracket_end_depth -= 1
                depth_changed = True
            elif char == ";":
                if current_param:
                    if (bracket_end_depth == 0 and depth_changed) or bracket_start_depth:
                        params.append((current_param.strip(), 1))
                    else:
                        params.append((current_param.strip(), 0))
                current_param = ""
                bracket_start_depth = bracket_end_depth
                depth_changed = False
            else:
                current_param += char

    # For each parameter extracted, infer the type given its info.
    typed_params = []
    for param in params:
        param_name = param[0]
        optional = param[1]
        try:
            typed_param = type_parameter(param_name, param_info[param_name.strip('"')])
            typed_params.append((typed_param, optional))
        except KeyError as e:
            logger.error(f"{func_name} Missing required parameter {param_name}: {e}")
            return None

    typed_signature = f"{func_name.upper()}("
    for typed_param in typed_params:
        typed_param_name = typed_param[0]
        optional = typed_param[1]
        if optional > 0:
            typed_signature += f"[{typed_param_name}]; "
        else:
            typed_signature += f"{typed_param_name}; "

    typed_signature = typed_signature.rstrip("; ") + ")"

    return typed_signature


def extract_function_info(path: str) -> dict:
    """
    Extract function information from HTML file
    :param path: str with the path of the HTML file
    :return: dict with typed function information
    """
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        embeds = soup.find_all("div", {"class": "embedded"})  # Good value to anchor on (just above)
        function_info = {}  # Final return value with information about function and types
        for embed in embeds:
            if embed.text.strip().lower() != "syntax":  # Key anchor term. If missing, try next
                continue

            # Next sibling is the definition (99% accurate, likely some edgecases that could be fixed)
            func_def = embed.find_next_sibling()
            func_name = re.match(r"^=?(.+)\s*\(.*\)$", func_def.text.strip())  # Match function name
            if func_name:
                func_name = func_name.group(1).strip().lower()
                if "rand" not in func_name:  # Avoid any random generation functions
                    logger.debug(f"Found: {func_name}")  # For debugging, print out captured name
                    param_info = {}  # Store a param name (Key) with the description (value)
                    current_tag = func_def.find_next_sibling()  # Prime description capture loop
                    # used to look ahead a handful of siblings for parameter descriptions
                    for _ in range(10):
                        if current_tag is None:  # Leave early if past page content
                            break
                        elif current_tag.name == "div" and current_tag.find("h4"):  # Leave if at next major block
                            header = current_tag.find("h4")
                            if header and ("example" in header.text.lower() or "syntax" in header.text.lower()):
                                break

                        # These should be the key parts that hold the parameter names with descriptions
                        # TODO Is there a better way to identify params than EMPH? A handful of edgecases exist without
                        # Edgecase: Finance3 VDB Start gets keyed as 'S' because of crappy description
                        # TODO: Maybe rewrite this segment to be more of the parser that "create_typed_signature" does?
                        if (current_tag.name == "p" or current_tag.name == "div") and current_tag.find("span", {"class": "emph"}):
                            emph_spans = current_tag.find_all("span", {"class": "emph"})  # Stores param
                            for span in emph_spans:
                                param_name = span.text.strip().lower()  # Name of argument
                                param_text = current_tag.text.strip().lower()  # Full line (Name + Description of argument)
                                logger.debug(f"PARAM {param_name}: {param_text}")
                                if ";" in param_name and "…" in param_name:  # Multi-parameter description
                                    # Get first occurrence
                                    base_match = re.match(r"^(\w+)\s+\d+", param_name)
                                    if base_match:
                                        base_name = base_match.group(1).lower()  # Match only the first word of recurring param
                                        logger.debug(f"Recurring param. Using '{base_name} N'")
                                        param_info[f"{base_name} N"] = param_text
                                else:
                                    param_info[param_name] = param_text

                        # Proceed to next sibling to identify any other parameters defined
                        current_tag = current_tag.find_next_sibling()

                    # Send a function syntax definition and the dictionary of parameters to descriptions for typing
                    typed_signature = create_typed_signature(func_def.text.strip(), param_info)
                    if typed_signature:
                        function_info[func_name] = typed_signature
    return function_info


def process_all(base_dir: str):
    """
    Process all HTML files within the provided base directory, the end results will be stored in new txt files4
    :param base_dir: str with the base directory to begin processing
    :return: None, output written to disk"""
    to_check = deque()  # Store additional directories to parse files from
    to_check.append(base_dir)  # Prime queue with first directory
    stats = {"processed": 0, "functions": 0}
    while len(to_check) > 0:  # While there are still directories to parse
        for root, dirs, files in os.walk(to_check.popleft()):  # Read all directory contents
            for d in dirs:  # Add each new directory to queue
                to_check.append(os.path.join(root, d))
            for file in files:  # Parse each discovered file
                if file.endswith(".html"):  # Only use the "HTML" files
                    if os.path.exists(os.path.join(root, f"{file}.txt")):
                        # Remove existing grammar if rebuilding to avoid excess clutter
                        logger.info("Removing existing extracted text file")
                        os.remove(os.path.join(root, f"{file}.txt"))
                    logger.info("Now processing file: " + file)  # Then process the file as normal
                    functions = extract_function_info(os.path.join(root, file))
                    if functions:
                        stats["processed"] += 1
                        stats["functions"] += len(functions)
                        with open(f"{os.path.join(root, file)}.txt", "a") as outfile:
                            for func_name, typed_signature in functions.items():
                                outfile.write(f"{typed_signature}\n")
                                logger.info(f"Wrote {func_name}")
    logger.info("Brief statistics:")
    logger.info(f"Num files: {stats['processed']}")
    logger.info(f"Num functions: {stats['functions']}")


if __name__ == "__main__":
    # definition = "ACCRINTM(Issue; Settlement; Rate [; Par [; Basis]])"
    # param_info = {
    #     "Issue": "Issue (required) is the issue date of the security.",
    #     "Settlement": "Settlement (required) is the date at which the interest accrued up until then is to be calculated.",
    #     "Rate": "Rate (required) is the annual nominal rate of interest (coupon interest rate).",
    #     "Par": "Par (optional) is the par value of the security. If omitted, a default value of 1000 is used.",
    #     "Basis": "Basis (optional) is chosen from a list of options and indicates how the year is to be calculated.",
    # }
    #
    # create_typed_signature(definition, param_info)

    base_dir = os.path.abspath("page_scrapes")
    logger.info("Beginning extraction at " + base_dir)
    process_all(base_dir)
    logger.info("FINISHED")
