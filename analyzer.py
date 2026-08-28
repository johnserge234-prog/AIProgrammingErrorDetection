import os
from groq import Groq


# =========================================================
# GROQ CONFIGURATION
# =========================================================

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

MODEL_NAME = "llama-3.3-70b-versatile"


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
# FAST ERROR DETECTION
# =========================================================

def fast_analysis(language, error):

    error_lower = error.lower()

    # =====================================================
    # MISSING SEMICOLON
    # =====================================================

    if (
        "expected ';'" in error_lower
        or "expected ';' before" in error_lower
        or "expected ';' at end" in error_lower
        or "missing ';'" in error_lower
        or "expected primary-expression before" in error_lower
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
    # MISSING CLOSING BRACE
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
    # MISSING QUOTATION
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
    # JAVA SYNTAX ERRORS
    # =====================================================

    if " ';' expected" in error_lower:

        return {
            "type": "Syntax Error",
            "explanation": (
                "Java expected a semicolon at this location."
            ),
            "suggestion": (
                "Add ';' at the end of the statement."
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
# MAIN ANALYZER
# =========================================================

def explain(language, code, compiler_error):

    # -----------------------------------------------------
    # NO ERROR
    # -----------------------------------------------------

    if not compiler_error or not compiler_error.strip():

        return {
            "type": "No Error",
            "explanation": "Your code is right."
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

        return mismatch

    # -----------------------------------------------------
    # FAST RULE-BASED ANALYSIS
    # -----------------------------------------------------

    quick_result = fast_analysis(
        language,
        compiler_error
    )

    if quick_result:

        print("FAST ANALYSIS USED")

        return quick_result

    # -----------------------------------------------------
    # ONLY UNKNOWN ERRORS GO TO GROQ
    # -----------------------------------------------------

    print("UNKNOWN ERROR")
    print("Sending error to Groq...")

    error_text = compiler_error.strip()

    if len(error_text) > 2000:
        error_text = error_text[:2000]

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

        print("GROQ ANALYSIS STARTED")

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

        print("GROQ RESPONSE RECEIVED")

        if not response.choices:
            raise Exception("Groq returned no response.")

        ai_response = response.choices[0].message.content

        if not ai_response:
            raise Exception("Groq returned an empty response.")

        ai_response = ai_response.strip()

        print("AI RESPONSE:")
        print(ai_response)

        # -------------------------------------------------
        # PARSE TYPE
        # -------------------------------------------------

        error_type = "Programming Error"
        explanation = ai_response
        suggestion = ""

        if "TYPE:" in ai_response:

            type_part = ai_response.split(
                "TYPE:",
                1
            )[1]

            if "EXPLANATION:" in type_part:

                error_type = type_part.split(
                    "EXPLANATION:",
                    1
                )[0].strip()

        # -------------------------------------------------
        # PARSE EXPLANATION
        # -------------------------------------------------

        if "EXPLANATION:" in ai_response:

            explanation_part = ai_response.split(
                "EXPLANATION:",
                1
            )[1]

            if "SUGGESTION:" in explanation_part:

                explanation = explanation_part.split(
                    "SUGGESTION:",
                    1
                )[0].strip()

            else:

                explanation = explanation_part.strip()

        # -------------------------------------------------
        # PARSE SUGGESTION
        # -------------------------------------------------

        if "SUGGESTION:" in ai_response:

            suggestion = ai_response.split(
                "SUGGESTION:",
                1
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