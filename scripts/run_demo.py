"""One-command demo: start the services, run scenarios S02-S05, clean up.

Uses free ports and a fresh, seeded temporary database, so services that are
already running and the repository's txn.db are left alone.

    python scripts/run_demo.py
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {
    "TXN_URL": "services.txn.main:app",
    "COMPLIANCE_URL": "services.compliance.main:app",
    "RAIL_URL": "services.rail_mock.main:app",
}
STARTUP_SECONDS = 30


def free_ports(count):
    """Hold all sockets open while choosing, so the ports are distinct."""
    sockets = [socket.socket() for _ in range(count)]
    try:
        for s in sockets:
            s.bind(("127.0.0.1", 0))
        return [s.getsockname()[1] for s in sockets]
    finally:
        for s in sockets:
            s.close()


def wait_until_ready(process, app, url, log):
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline and process.poll() is None:
        try:
            httpx.get(f"{url}/openapi.json", timeout=2).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise RuntimeError(f"{app} did not start:\n{log.read_text(errors='replace')}")


def run(workdir):
    urls = {name: f"http://127.0.0.1:{port}"
            for name, port in zip(SERVICES, free_ports(len(SERVICES)))}
    env = {**os.environ, **urls, "PYTHONPATH": str(ROOT),
           "PYTHONDONTWRITEBYTECODE": "1",
           "DATABASE_URL": f"sqlite:///{(workdir / 'txn.db').as_posix()}"}

    subprocess.run([sys.executable, "-m", "services.txn.seed"],
                   cwd=ROOT, env=env, check=True)
    processes = {}
    try:
        for name, app in SERVICES.items():
            # cwd matters: the Transaction service opens txn.db for its outbox.
            with (workdir / f"{name}.log").open("w") as log:
                processes[name] = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", app,
                     "--port", urls[name].rsplit(":", 1)[-1]],
                    cwd=workdir, env=env, stdout=log, stderr=subprocess.STDOUT)
        for name, app in SERVICES.items():
            wait_until_ready(processes[name], app, urls[name], workdir / f"{name}.log")
            print(f"Started {app} on {urls[name]}", flush=True)

        return subprocess.run([sys.executable, "-m", "tests.scenarios.run_scenarios"],
                              cwd=ROOT, env=env).returncode
    finally:
        for process in processes.values():
            process.terminate()
        for process in processes.values():
            process.wait()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        sys.exit(run(Path(tmp)))
