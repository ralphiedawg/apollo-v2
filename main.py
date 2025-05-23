import subprocess
from core.chat import chat_with_apollo


def run_health_check():
    subprocess.run(["./go/apolloctl"])

if __name__ == "__main__":
    run_health_check()
    chat_with_apollo()
