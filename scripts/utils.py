"""Utilities used by project scripts."""

import subprocess

ERROR: str = "\033[31m"
CLEAR: str = "\033[0m"
BOLD: str = "\033[1m"
SUCCESS: str = "\033[32;1m"


def run_command(command: str):
    """Run a command in the shell and print its output. Returns False if the
    return code is not 0, True otherwise."""

    def print_output(output):
        print(output.strip().decode())

    def print_error(error_output):
        print(ERROR + error_output.strip().decode() + CLEAR)

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    while True:
        output = process.stdout.readline()
        error = process.stderr.readline()
        print_output(output) if output else None
        print_error(error) if error else None

        status_code = process.poll()
        if status_code is not None:
            for output in process.stdout.readlines():
                print_output(output)
            for error_output in process.stderr.readlines():
                print_error(error_output)
            if status_code != 0:
                return False
            break
    return True


def print_bold(text: str):
    print(BOLD + text + CLEAR)


def print_success(text: str):
    print(SUCCESS + text + CLEAR)


def print_error(error_text: str):
    print(ERROR + error_text + CLEAR)
