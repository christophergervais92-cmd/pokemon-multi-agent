#!/usr/bin/env python3
"""
Standalone task runner entrypoint.

Run:
  python3 agents/run_task_runner.py
"""

from __future__ import annotations

import os
import time

from tasks.runner import get_task_runner, RunnerConfig, TaskRunner


def main() -> None:
    max_workers = int(os.environ.get("TASK_RUNNER_MAX_WORKERS", "4"))
    loop_sleep = float(os.environ.get("TASK_RUNNER_LOOP_SLEEP_SECONDS", "1.0"))

    runner = TaskRunner(RunnerConfig(max_workers=max_workers, loop_sleep_seconds=loop_sleep))
    runner.start()

    print("[TaskRunner] running (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[TaskRunner] stopping...")
        runner.stop()


if __name__ == "__main__":
    main()

