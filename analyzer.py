import os
import re
from groq import Groq


# =========================================================
# GROQ CONFIGURATION
# =========================================================

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

MODEL_NAME = "openai/gpt-oss-120b"

MAX_ERRORS = 10


# =========================================================
# SHARED PATTERN: "missing semicolon" detection
#
# g++ often lists several valid alternatives before naming
# what token actually follows — e.g. "expected ',' or ';'
# before 'cout'" — not just "expected ';' before 'cout'".
# This matches a quoted semicolon appearing ANYWHERE between
# "expected" and "before", so it catches those alternatives
# too, while still correctly rejecting the opposite case
# ("expected primary-expression before ';'", where an EXTRA
# semicolon is the actual problem, not a missing one — there
# the semicolon appears AFTER "before", so it won't match).
# Used both to shift g++'s off-by-one line number back to the
# real culprit line, and to classify the error via
# fast_analysis(), so both stay in sync with each other.
# =========================================================

MISSING_SEMICOLON_PATTERN = re.compile(
    r"expected\b.*?[\"'\u2018\u2019];[\"'\u2018\u2019].*?\bbefore\b"
)


def is_missing_semicolon_message(message_lower):
    return bool(MISSING_SEMICOLON_PATTERN.search(message_lower))


# =========================================================
# LANGUAGE MISMATCH
# =========================================================

def detect_language_mismatch(language, code):

    selected = language.strip().lower()
    source = code.lower()

    java_indicators = [
        "public class",
        "public static void main",
        "system.out.println",
        "system.out.print",
        "import java.",
        "string[] args",
        "scanner"
    ]

    cpp_indicators = [
        "#include <iostream>",
        "#include<iostream>",
        "using namespace std",
        "cout <<",
        "cin >>",
        "std::cout",
        "std::cin",
        "endl"
    ]

    java_score = sum(
        1 for item in java_indicators
        if item in source
    )

    cpp_score = sum(
        1 for item in cpp_indicators
        if item in source
    )

    if selected in ["c++", "cpp", "cplusplus"]:

        if java_score > cpp_score and java_score > 0:

            return {
                "type": "Language Mismatch",
                "explanation": (
                    "You selected C++, but the source code "
                    "appears to be written in Java."
                ),
                "suggestion": (
                    "Select Java from the programming "
                    "language menu if this is Java code."
                )
            }

    if selected == "java":

        if cpp_score > java_score and cpp_score > 0:

            return {
                "type": "Language Mismatch",
                "explanation": (
                    "You selected Java, but the source code "
                    "appears to be written in C++."
                ),
                "suggestion": (
                    "Select C++ from the programming "
                    "language menu if this is C++ code."
                )
            }

    return None


# =========================================================
# PARSE INDIVIDUAL ERRORS OUT OF RAW COMPILER OUTPUT
# =========================================================

def parse_errors(language, raw_error):

    language = (language or "").strip().lower()
    entries = []

    if language == "java":

        # javac format: Main.java:5: error: ';' expected
        pattern = re.compile(
            r'^.+\.java:(\d+):\s*error:\s*(.+)$',
            re.MULTILINE
        )

    else:

        # g++ format: Main.cpp:5:9: error: expected ';' ...
        pattern = re.compile(
            r'^.+\.cpp:(\d+):\d+:\s*error:\s*(.+)$',
            re.MULTILINE
        )

    raw_entries = []

    for match in pattern.finditer(raw_error):

        line_number = int(match.group(1))
        message = match.group(2).strip()

        # -------------------------------------------------
        # g++ ONLY: a missing semicolon isn't discovered
        # until the parser reaches the START of the NEXT
        # statement, so g++ reports it one line too late.
        # Shift the reported line back by one to match where
        # the mistake actually is.
        # -------------------------------------------------

        message_lower = message.lower()

        if (
            language != "java"
            and is_missing_semicolon_message(message_lower)
            and line_number > 1
        ):
            line_number -= 1

        raw_entries.append({
            "line": line_number,
            "message": message
        })

    # -----------------------------------------------------
    # DEDUPLICATE: a single real mistake (e.g. a missing
    # brace) often makes the compiler cascade into several
    # confusing follow-up messages. Keep only the first
    # message reported per line so the result stays readable.
    # -----------------------------------------------------

    entries = []
    seen_lines = set()

    for entry in raw_entries:

        if entry["line"] in seen_lines:
            continue

        seen_lines.add(entry["line"])
        entries.append(entry)

    # -----------------------------------------------------
    # FILTER OUT KNOWN CASCADE NOISE: after one real
    # structural mistake (e.g. a missing brace), compilers
    # often throw a few vague follow-up messages that aren't
    # independent lessons on their own. Drop them — unless
    # doing so would leave nothing at all.
    # -----------------------------------------------------

    NOISE_PHRASES = [
        "class, interface, enum, or record expected",
        "class, interface, or enum expected",
        "illegal start of type",
    ]

    def is_noise(message):
        message_lower = message.lower()
        return any(
            phrase in message_lower
            for phrase in NOISE_PHRASES
        )

    filtered = [
        entry for entry in entries
        if not is_noise(entry["message"])
    ]

    if filtered:
        entries = filtered

    return entries


# =========================================================
# FAST ERROR DETECTION (operates on ONE error message)
# =========================================================

def fast_analysis(language, error):

    error_lower = error.lower()

    # =====================================================
    # MISSING QUOTATION
    # (checked first: an unclosed string often cascades into
    # a misleading "expected ';'" error further down)
    # =====================================================

    if (
        "missing terminating" in error_lower
        or "unclosed string" in error_lower
    ):

        return {
            "type": "String Error",
            "explanation": (
                "A string or character is missing its "
                "closing quotation mark."
            ),
            "suggestion": (
                "Check the quotation marks and add the "
                "missing closing quotation mark."
            )
        }

    # =====================================================
    # MISSING CLOSING BRACE
    # (checked before semicolon: an unclosed brace often
    # cascades into a misleading "expected ';'" error too)
    # =====================================================

    if (
        "expected '}'" in error_lower
        or "expected ‘}’" in error_lower
        or "reached end of file while parsing" in error_lower
    ):

        return {
            "type": "Bracket Error",
            "explanation": (
                "A closing curly brace '}' is missing or the "
                "braces in the program are not properly matched."
            ),
            "suggestion": (
                "Check every opening '{' and make sure it has "
                "a corresponding closing '}'."
            )
        }

    # =====================================================
    # MISSING CLOSING PARENTHESIS
    # =====================================================

    if (
        "expected ')'" in error_lower
        or "expected ‘)’" in error_lower
    ):

        return {
            "type": "Parenthesis Error",
            "explanation": (
                "A closing parenthesis ')' is missing."
            ),
            "suggestion": (
                "Check the parentheses in the affected "
                "statement and add the missing ')'."
            )
        }

    # =====================================================
    # MISSING OPENING PARENTHESIS
    # =====================================================

    if (
        "expected '(' before" in error_lower
        or "expected ‘(’ before" in error_lower
    ):

        return {
            "type": "Parenthesis Error",
            "explanation": (
                "An opening parenthesis '(' is missing."
            ),
            "suggestion": (
                "Add '(' in the position indicated by "
                "the compiler."
            )
        }

    # =====================================================
    # MISSING OPENING BRACE
    # =====================================================

    if (
        "'{' expected" in error_lower
        or "expected '{'" in error_lower
    ):

        return {
            "type": "Bracket Error",
            "explanation": (
                "An opening curly brace '{' is missing — "
                "usually right after a class or method "
                "declaration."
            ),
            "suggestion": (
                "Add '{' at the position indicated by the "
                "compiler to begin the class or method body."
            )
        }

    # =====================================================
    # MISSING SEMICOLON
    # (includes g++'s "expected ',' or ';' before X" phrasing,
    # not just the simple "expected ';' before X" case)
    # =====================================================

    if (
        "expected ';'" in error_lower
        or "';' expected" in error_lower
        or "missing ';'" in error_lower
        or "expected primary-expression before" in error_lower
        or is_missing_semicolon_message(error_lower)
    ):

        return {
            "type": "Syntax Error",
            "explanation": (
                "A semicolon ';' is missing from a statement. "
                "The compiler expected the statement to end "
                "with a semicolon."
            ),
            "suggestion": (
                "Add ';' at the end of the statement identified "
                "by the compiler."
            )
        }

    # =====================================================
    # MISSING #include <iostream>
    # (checked before the generic undeclared-variable rule,
    # since 'cout'/'cin'/'endl' being undeclared almost
    # always means the header is missing, not a real typo)
    # =====================================================

    if (
        "was not declared in this scope" in error_lower
        or "was not declared" in error_lower
    ) and (
        "'cout'" in error_lower
        or "'cin'" in error_lower
        or "'endl'" in error_lower
        or "cout" in error_lower and "std" in error_lower
    ):

        return {
            "type": "Missing Include",
            "explanation": (
                "'cout', 'cin', or 'endl' is not recognized "
                "because the header that defines them was not "
                "included."
            ),
            "suggestion": (
                "Add '#include <iostream>' at the top of the "
                "file, above 'using namespace std;'."
            )
        }

    # =====================================================
    # C++ UNDECLARED VARIABLE
    # =====================================================

    if (
        "was not declared in this scope" in error_lower
        or "was not declared" in error_lower
    ):

        return {
            "type": "Variable Error",
            "explanation": (
                "The variable you used has not been declared, "
                "or its name does not match the declaration."
            ),
            "suggestion": (
                "Declare the variable before using it and "
                "check that its spelling is correct."
            )
        }

    # =====================================================
    # JAVA CANNOT FIND SYMBOL
    # =====================================================

    if "cannot find symbol" in error_lower:

        return {
            "type": "Variable or Reference Error",
            "explanation": (
                "Java cannot find the variable, method, or "
                "class referenced in your code."
            ),
            "suggestion": (
                "Check the spelling and make sure the variable, "
                "method, or class has been declared."
            )
        }

    # =====================================================
    # JAVA ILLEGAL SYMBOL
    # =====================================================

    if "illegal start of expression" in error_lower:

        return {
            "type": "Syntax Error",
            "explanation": (
                "The compiler found code in a position where "
                "that expression is not valid."
            ),
            "suggestion": (
                "Check the syntax around the line reported "
                "by the compiler."
            )
        }

    # =====================================================
    # UNKNOWN
    # =====================================================

    return None


# =========================================================
# AI FALLBACK FOR A SINGLE UNRECOGNIZED ERROR
# =========================================================

def ai_explain_single(language, code, error_text):

    error_text = error_text.strip()

    if len(error_text) > 1000:
        error_text = error_text[:1000]

    source_code = code.strip()

    if len(source_code) > 4000:
        source_code = source_code[:4000]

    prompt = f"""
You are a beginner programming tutor.

Language:
{language}

Compiler error:
{error_text}

Student code:
{source_code}

Explain the actual compiler error.

Do not invent an error.

Return exactly:

TYPE:
[error type]

EXPLANATION:
[short explanation]

SUGGESTION:
[specific fix]
"""

    try:

        if not os.environ.get("GROQ_API_KEY"):
            raise Exception("GROQ_API_KEY is not set in the environment.")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain C++ and Java compiler "
                        "errors accurately and briefly."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            timeout=20
        )

        if not response.choices:
            raise Exception("Groq returned no response.")

        ai_response = response.choices[0].message.content

        if not ai_response:
            raise Exception("Groq returned an empty response.")

        ai_response = ai_response.strip()

        error_type = "Programming Error"
        explanation = ai_response
        suggestion = ""

        if "TYPE:" in ai_response:

            type_part = ai_response.split("TYPE:", 1)[1]

            if "EXPLANATION:" in type_part:
                error_type = type_part.split(
                    "EXPLANATION:", 1
                )[0].strip()

        if "EXPLANATION:" in ai_response:

            explanation_part = ai_response.split(
                "EXPLANATION:", 1
            )[1]

            if "SUGGESTION:" in explanation_part:
                explanation = explanation_part.split(
                    "SUGGESTION:", 1
                )[0].strip()
            else:
                explanation = explanation_part.strip()

        if "SUGGESTION:" in ai_response:

            suggestion = ai_response.split(
                "SUGGESTION:", 1
            )[1].strip()

        return {
            "type": error_type,
            "explanation": explanation,
            "suggestion": suggestion
        }

    except Exception as e:

        print("GROQ ERROR:", e)

        return {
            "type": "AI Analysis Error",
            "explanation": (
                "The compiler detected an error, but the "
                "AI could not provide an explanation."
            ),
            "suggestion": (
                "The compiler error can still be reviewed "
                "to identify the problem."
            )
        }


# =========================================================
# MAIN ANALYZER
# =========================================================

def explain(language, code, compiler_error):

    # -----------------------------------------------------
    # NO ERROR
    # -----------------------------------------------------

    if not compiler_error or not compiler_error.strip():

        return {
            "type": "No Error",
            "explanation": "Your code is right.",
            "suggestion": "",
            "errors": []
        }

    # -----------------------------------------------------
    # LANGUAGE MISMATCH
    # -----------------------------------------------------

    mismatch = detect_language_mismatch(
        language,
        code
    )

    if mismatch:

        print("LANGUAGE MISMATCH DETECTED")

        mismatch["errors"] = []
        return mismatch

    # -----------------------------------------------------
    # PARSE OUT EACH INDIVIDUAL ERROR + ITS LINE NUMBER
    # -----------------------------------------------------

    entries = parse_errors(language, compiler_error)

    truncated = False

    if not entries:

        # Raw output didn't match the expected compiler format
        # (e.g. "Java compiler could not be found", a timeout
        # message, or an unusual error). Treat it as one
        # line-less entry so it still gets analyzed.

        entries = [{
            "line": None,
            "message": compiler_error.strip()
        }]

    elif len(entries) > MAX_ERRORS:

        entries = entries[:MAX_ERRORS]
        truncated = True

    # -----------------------------------------------------
    # ANALYZE EACH ERROR INDIVIDUALLY
    # -----------------------------------------------------

    results = []

    for entry in entries:

        quick_result = fast_analysis(language, entry["message"])

        if quick_result:

            print(f"FAST ANALYSIS USED (line {entry['line']})")

            results.append({
                "line": entry["line"],
                "type": quick_result["type"],
                "explanation": quick_result["explanation"],
                "suggestion": quick_result["suggestion"]
            })

        else:

            print(f"UNKNOWN ERROR (line {entry['line']}) — asking Groq")

            ai_result = ai_explain_single(
                language,
                code,
                entry["message"]
            )

            results.append({
                "line": entry["line"],
                "type": ai_result["type"],
                "explanation": ai_result["explanation"],
                "suggestion": ai_result["suggestion"]
            })

    # -----------------------------------------------------
    # BUILD TOP-LEVEL SUMMARY (for older/simple display)
    # -----------------------------------------------------

    if len(results) == 1:

        top_type = results[0]["type"]
        top_explanation = results[0]["explanation"]
        top_suggestion = results[0]["suggestion"]

    else:

        top_type = f"{len(results)} Errors Found"
        top_explanation = (
            "Multiple errors were found in your code. "
            "See the list below for each one."
        )
        top_suggestion = ""

        if truncated:
            top_explanation += (
                f" Showing the first {MAX_ERRORS} errors detected."
            )

    return {
        "type": top_type,
        "explanation": top_explanation,
        "suggestion": top_suggestion,
        "errors": results
    }