import os
import shutil
import subprocess
import tempfile


# ============================================================
# FIND JAVA COMPILER
# ============================================================

def find_javac():

    javac = shutil.which("javac")

    if javac:
        return javac

    java_home = os.environ.get("JAVA_HOME")

    if java_home:

        possible_path = os.path.join(
            java_home,
            "bin",
            "javac.exe"
        )

        if os.path.isfile(possible_path):
            return possible_path

    common_locations = [
        r"C:\Program Files\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"C:\Program Files\Amazon Corretto"
    ]

    for base_folder in common_locations:

        if not os.path.exists(base_folder):
            continue

        try:

            for folder_name in os.listdir(base_folder):

                folder_path = os.path.join(
                    base_folder,
                    folder_name
                )

                javac_path = os.path.join(
                    folder_path,
                    "bin",
                    "javac.exe"
                )

                if os.path.isfile(javac_path):
                    return javac_path

        except PermissionError:
            continue

    return None


# ============================================================
# FIND C++ COMPILER
# ============================================================

def find_gpp():

    gpp = shutil.which("g++")

    if gpp:
        return gpp

    possible_locations = [
        r"C:\mingw64\bin\g++.exe",
        r"C:\mingw-w64\bin\g++.exe",
        r"C:\MinGW\bin\g++.exe",
        r"C:\Program Files\mingw64\bin\g++.exe",
        r"C:\Program Files\mingw-w64\bin\g++.exe"
    ]

    for path in possible_locations:

        if os.path.isfile(path):
            return path

    return None


# ============================================================
# COMPILE C++
# ============================================================

def compile_cpp(code):

    if not code or not code.strip():
        return "No C++ code was provided."

    gpp = find_gpp()

    if not gpp:
        return (
            "C++ compiler could not be found by the system."
        )

    try:

        with tempfile.TemporaryDirectory() as temp_dir:

            source_file = os.path.join(
                temp_dir,
                "Main.cpp"
            )

            output_file = os.path.join(
                temp_dir,
                "Main.exe"
            )

            with open(
                source_file,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(code)

            result = subprocess.run(
                [
                    gpp,
                    source_file,
                    "-o",
                    output_file
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:

                error = result.stderr.strip()

                if error:
                    return error

                return "C++ compilation failed."

            return ""

    except subprocess.TimeoutExpired:

        return (
            "C++ compilation took too long and was stopped."
        )

    except Exception as e:

        return f"C++ compiler error: {str(e)}"


# ============================================================
# COMPILE JAVA
# ============================================================

def compile_java(code):

    if not code or not code.strip():
        return "No Java code was provided."

    javac = find_javac()

    if not javac:
        return (
            "Java compiler could not be found by the system."
        )

    try:

        with tempfile.TemporaryDirectory() as temp_dir:

            source_file = os.path.join(
                temp_dir,
                "Main.java"
            )

            with open(
                source_file,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(code)

            result = subprocess.run(
                [
                    javac,
                    source_file
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:

                error = result.stderr.strip()

                if error:
                    return error

                return "Java compilation failed."

            return ""

    except subprocess.TimeoutExpired:

        return (
            "Java compilation took too long and was stopped."
        )

    except Exception as e:

        return f"Java compiler error: {str(e)}"


# ============================================================
# GENERAL COMPILER
# ============================================================

def compile_code(language, code):

    if not language:

        return (
            "Programming language was not specified."
        )

    language = language.strip().lower()

    if language in ["c++", "cpp", "cplusplus"]:

        return compile_cpp(code)

    elif language == "java":

        return compile_java(code)

    else:

        return (
            "Unsupported programming language. "
            "Only C++ and Java are supported."
        )