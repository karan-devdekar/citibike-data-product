import os
import subprocess
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_dbt(command):
    print(f"Starting: dbt {command}", flush=True)

    result = subprocess.run(
        ["dbt"] + command.split() + ["--profiles-dir", BASE_DIR],
        check=False,
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        print(
            f"dbt {command} failed with exit code {result.returncode}",
            flush=True
        )
        sys.exit(result.returncode)

    print(f"Completed: dbt {command}", flush=True)


if __name__ == "__main__":
    run_dbt("run")
    run_dbt("test")

    print("DBT PIPELINE COMPLETED SUCCESSFULLY", flush=True)
