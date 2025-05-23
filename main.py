import subprocess

def run_health_check():
    subprocess.run(["./go/apolloctl"])

if __name__ == "__main__":
    run_health_check()
