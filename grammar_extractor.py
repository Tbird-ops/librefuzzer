#!/usr/bin/env python
# @Name: grammar_extractor.py
# @Project: librefuzzer
# @Author: Tristan Stapert
# @Created: 11/14/2025
# @Version: 0.3

import os
import re
from collections import deque
from bs4 import BeautifulSoup
import logging

# Easier logging control for tracking program status
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("INITIALIZED")


# TODO Clean this up.
# - Duplicate values
# - Diff between number/integer??
# - Probably other things
def infer_type(param_name: str, description: str) -> str:
    """
    Infer the specific type of parameter based on its name and description.
    Returns a type annotation string.
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


def type_parameter(param: str, param_description: dict) -> str:
    """Add inferred typing information to a provided parameter, given its description"""
    is_optional = param.startswith("[") and param.endswith("]")
    if is_optional:
        param = param[1:-1].strip()  # Remove brackets from optional parameter

    if param.startswith('"') and param.endswith('"'):
        typed = f"{param}: String"
    else:
        # TODO THIS SEEMS VERY SIMILAR TO "extract_function_info" SEGMENT
        # Extract parameter name (handle repeating occurrences such as Logical 1 [; Logical 2 [; ...
        param_name = param.split("[")[0].strip()

        # Handle ... continuations
        if "…" in param:
            # Extract base case
            base_match = re.match(r"^(\w+)\s+\d+", param_name)
            if base_match:
                base_name = base_match.group(1)
                param_name = f"{base_name} N"

        description = ""
        for desc_key in param_description:
            if param_name in desc_key or desc_key in param_name:
                description = param_description[desc_key]
                break

        param_type = infer_type(param_name, description)
        typed = f"{param}: {param_type}"

    # Re-add optional brackets
    if is_optional:
        typed = f"[{typed}]"

    return typed


def create_typed_signature(syntax: str, param_info: dict) -> str:
    """Gather information and prepare a function definition for inferred typing"""
    # parse signature (Group 1 is the function name, Group 2 is the parameter list)
    match = re.match(r"^=?(.+)\s*\((.*)\)\s*", syntax)
    if not match:
        logger.error("Syntax not matched: " + syntax)
        return syntax  # When failures occur, just return the existing definition syntax

    func_name = match.group(1)
    params_str = match.group(2)

    if not params_str.strip():
        logger.error("No params for: " + func_name)
        return syntax  # Same as above, but that some functions don't have parameters. Ex: Datetime NOW() -> current time

    # Split parameters, handle optional nesting
    params = []
    current_param = ""
    bracket_depth = 0

    for char in params_str + ";":
        if char == "[":
            bracket_depth += 1
            current_param += char
        elif char == "]":
            bracket_depth -= 1
            current_param += char
        elif char == ";" and bracket_depth == 0:
            if current_param.strip():
                params.append(current_param)
            current_param = ""
        else:
            current_param += char

    # For each parameter extracted, infer the type given its info.
    typed_params = []
    for param in params:
        typed_param = type_parameter(param, param_info)
        typed_params.append(typed_param)


def extract_function_info(path: str) -> dict:
    """Extract function information from HTML file"""
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        embeds = soup.find_all("div", {"class": "embedded"})  # Good value to anchor on (just above)
        function_info = {}  # Final return value with information about function and types
        for embed in embeds:
            if embed.text.strip().lower() != "syntax":  # Key anchor term. If missing, try next
                continue

            # Next sibling is the definition (99% accurate, misses 1 spreadsheet func, acceptable (pivot table))
            func_def = embed.find_next_sibling()
            func_name = re.match(r"^=?(.+)\s*\(.*\)$", func_def.text.strip())  # Match function name
            if func_name:
                logger.debug(func_name.group(1))  # For debugging, print out captured name
                param_info = {}  # Store a param name (Key) with the description (value)
                current_tag = func_def.find_next_sibling()  # Prime description capture loop
                # used to look ahead a handful of siblings for parameter descriptions
                for _ in range(10):
                    if current_tag is None:  # Leave early if past page content
                        break
                    elif current_tag.name == "div" and current_tag.find("h4"):  # Leave if at next major block
                        header = current_tag.find("h4")
                        if header and ("Example" in header.text or "Syntax" in header.text):
                            break

                    # These should be the key parts that hold the parameter names with descriptions
                    if (current_tag.name == "p" or current_tag.name == "div") and current_tag.find("span", {"class": "emph"}):
                        emph_spans = current_tag.find_all("span", {"class": "emph"})  # Stores param
                        for span in emph_spans:
                            param_name = span.text.strip()  # Name of argument
                            param_text = current_tag.text.strip()  # Full line (Name + Description of argument)
                            logger.debug(f"PARAM {param_name}: {param_text}")
                            if ";" in param_name and "…" in param_name:  # Multi-parameter description
                                # Get first occurrence
                                base_match = re.match(r"^(\w+)\s+\d+", param_name)
                                if base_match:
                                    base_name = base_match.group(1)  # Match only the first word of recurring param
                                    logger.debug(f"Recurring param. Using {base_name}")
                                    param_info[f"{base_name} N"] = param_text
                            else:
                                logger.debug(f"Normal param. Using {param_name}")
                                param_info[param_name] = param_text

                    # Proceed to next sibling to identify any other parameters defined
                    current_tag = current_tag.find_next_sibling()

                # Send a function syntax definition and the dictionary of parameters to descriptions for typing
                typed_signature = create_typed_signature(func_def.text.strip(), param_info)
                function_info[func_name] = typed_signature
    return function_info


def process_all(base_dir: str):
    """Process all HTML files within the provided base directory, the end results will be stored in new txt files"""
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
                        with open(f"{os.path.join(root, file)}", "r") as outfile:
                            for func_name, typed_signature in functions.items():
                                outfile.write(typed_signature + "\n")
                                logger.info(f"Wrote {func_name}")
    logger.info("Brief statistics:")
    logger.info(f"Num files: {stats['processed']}")
    logger.info(f"Num functions: {stats['functions']}")


if __name__ == "__main__":
    base_dir = os.path.abspath("page_scrapes")
    logger.info("Beginning extraction at " + base_dir)
    process_all(base_dir)
    logger.info("FINISHED")
