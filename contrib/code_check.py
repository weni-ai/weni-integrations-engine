import os
import subprocess


class LogStyle:
    OK = '\033[92m'
    HEADER = '\033[95m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    WHITE = '\033[0m'


def log(output: str, log_style: str):
    print(LogStyle.WHITE, "└─", log_style + output, "\n")


def execute(cmd: str):
    os.chdir(os.getcwd())
    print(LogStyle.HEADER, "Running -", LogStyle.BOLD + cmd)

    try:
        subprocess.check_output(cmd, shell=True).decode("utf-8")
        log("Success", LogStyle.OK)
    except subprocess.CalledProcessError as e:
        print(LogStyle.FAIL, e.stdout.decode("utf-8").replace("\n", "\n ").strip())
        log("Fail", LogStyle.FAIL)
        exit(1)


if __name__ == "__main__":
    if not os.getcwd().endswith("weni-marketplace-engine"):
        raise Exception("The command need be executed in weni-marketplace-engine")

    execute("flake8 .")
