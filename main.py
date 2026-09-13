import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel

from compiler import compile_code
from analyzer import explain


app = FastAPI()


class CodeInput(BaseModel):
    language: str
    code: str


@app.on_event("startup")
def check_env():

    if not os.environ.get("GROQ_API_KEY"):
        print("========================================")
        print("WARNING: GROQ_API_KEY is not set.")
        print("Check that .env exists in this folder and")
        print("contains GROQ_API_KEY=your_key_here")
        print("========================================")
    else:
        print("GROQ_API_KEY loaded successfully.")


@app.get("/")
def home():
    return {
        "message": "AI Programming Error Detection Tool"
    }


@app.post("/analyze")
def analyze_code(data: CodeInput):

    print("========================================")
    print("ANDROID REQUEST RECEIVED")
    print("Language:", data.language)
    print("========================================")

    # ============================================
    # COMPILE THE CODE
    # ============================================

    print("Compiling code...")

    compiler_error = compile_code(
        data.language,
        data.code
    )

    if compiler_error:
        print("Compiler error detected:")
        print(compiler_error)
    else:
        print("No compiler error. Running logic-error review...")

    # ============================================
    # SEND TO ANALYZER
    # (explain() handles both cases internally:
    # if compiler_error is empty, it runs the AI
    # logic-error check; if not, it parses and
    # explains each compiler error)
    # ============================================

    result = explain(
        data.language,
        data.code,
        compiler_error
    )

    print("Analysis completed.")

    return result