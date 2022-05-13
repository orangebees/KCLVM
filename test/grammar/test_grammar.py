"""This is a scripts to run KCL grammar test cases"""
import pytest
import os
import subprocess
import re
import yaml
import pathlib

TEST_FILE = "main.k"
STDOUT_GOLDEN = "stdout.golden"
STDERR_GOLDEN = "stderr.golden"
STDOUT_GOLDEN_PY = "stdout.golden.py"
STDERR_GOLDEN_PY = "stderr.golden.py"
SETTINGS_FILE = "settings.yaml"


def find_test_dirs(path, category):
    result = []
    for root, dirs, files in os.walk(path + category):
        for name in files:
            if name == "main.k":
                result.append(root)
    return result


def compare_strings(result_strings, golden_strings):
    assert result_strings == golden_strings


def compare_results(result, golden_result):
    """Convert bytestring (result) and list of strings (golden_lines) both to
    list of strings with line ending stripped, then compare.
    """

    result_strings = result.decode().split("\n")
    golden_strings = golden_result.decode().split("\n")
    compare_strings(result_strings, golden_strings)


def compare_results_with_lines(result, golden_lines):
    """Convert bytestring (result) and list of strings (golden_lines) both to
    list of strings with line ending stripped, then compare.
    """

    result_strings = result.decode().split("\n")
    golden_strings = []
    for line in golden_lines:
        clean_line = re.sub("\n$", "", line)
        golden_strings.append(clean_line)
    # List generated by split() has an ending empty string, when the '\n' is
    # the last character
    assert result_strings[-1] == "", "The result string does not end with a NEWLINE"
    golden_strings.append("")
    compare_strings(result_strings, golden_strings)


def generate_golden_file(py_file_name):
    if os.path.isfile(py_file_name):
        try:
            process = subprocess.Popen(
                ["kclvm", py_file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ),
            )
            stdout, stderr = process.communicate()
            assert (
                process.returncode == 0
            ), "Error executing file {}, exit code = {}".format(
                py_file_name, process.returncode
            )
        except Exception:
            raise
        return stdout
    return None


def read_settings_file(settings_file_name):
    if os.path.isfile(settings_file_name):
        try:
            with open(settings_file_name, "r") as stream:
                settings = yaml.safe_load(stream)
        except Exception:
            raise
        return settings
    return None


print("##### K Language Grammar Test Suite #####")
test_dirs = find_test_dirs(str(pathlib.Path(__file__).parent), "")


@pytest.mark.parametrize("test_dir", test_dirs)
def test_grammar(test_dir):
    print("Testing {}".format(test_dir))
    test_settings = read_settings_file(os.path.join(test_dir, SETTINGS_FILE))
    kcl_command = ["kcl", TEST_FILE]
    if test_settings and test_settings["kcl_options"]:
        kcl_command.extend(test_settings["kcl_options"].split())
    process = subprocess.Popen(
        kcl_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.abspath(test_dir),
        env=dict(os.environ),
    )
    stdout, stderr = process.communicate()
    print("STDOUT:\n{}".format(stdout.decode()))
    print("STDERR:\n{}".format(stderr.decode()))
    RETURN_CODE = 0
    KCLVM_OUTPUT = 1
    GOLDEN_FILE = 2
    GOLDEN_FILE_SCRIPT = 3
    settings = {
        "stdout": (None, stdout, STDOUT_GOLDEN, STDOUT_GOLDEN_PY),
        "stderr": (1, stderr, STDERR_GOLDEN, STDERR_GOLDEN_PY),
    }
    for _, setting in settings.items():
        # Attempt to generate a golden stdout.
        golden_file_result = generate_golden_file(
            os.path.join(test_dir, setting[GOLDEN_FILE_SCRIPT])
        )
        if golden_file_result:
            compare_results(setting[KCLVM_OUTPUT], golden_file_result)
        else:
            # Attempt to use existing golden stdout.
            try:
                with open(
                    os.path.join(test_dir, setting[GOLDEN_FILE]), "r"
                ) as golden_file:
                    compare_results_with_lines(setting[KCLVM_OUTPUT], golden_file)
                if setting[RETURN_CODE] is not None:
                    assert process.returncode == setting[RETURN_CODE]
            except OSError:
                # Ignore when a golden file does not exist.
                pass
            except Exception:
                raise