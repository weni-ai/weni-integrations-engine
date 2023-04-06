import os
import subprocess


class LogStyle:
    OK = "\033[92m"
    HEADER = "\033[95m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    WHITE = "\033[0m"


def log(output: str, log_style: str):
    print(LogStyle.WHITE, "└─", log_style + output, "\n")


def execute(cmd: str, cmd_output: bool = False):
    os.chdir(os.getcwd())
    print(LogStyle.HEADER, "Running -", LogStyle.BOLD + cmd)

    try:
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        log("Success", LogStyle.OK)

        if cmd_output:
            print(LogStyle.OK, "\nCommand output: \n\n", output)

    except subprocess.CalledProcessError as e:
        print(LogStyle.FAIL, e.stdout.decode("utf-8").replace("\n", "\n ").strip())
        log("Fail", LogStyle.FAIL)
        exit(1)


if __name__ == "__main__":
    if not os.getcwd().endswith("weni-integrations-engine"):
        raise Exception("The command need be executed in weni-marketplace-engine")

    log("Make any missing migrations", LogStyle.BOLD)
    execute("python manage.py makemigrations")

    # Lint validations
    execute("flake8 marketplace/")
    # Coverage tests
    execute("coverage run manage.py test --verbosity=2 --noinput")
    execute("coverage report -m", cmd_output=True)
