import importlib.metadata
import json
import os
import shutil
import sys


FORBIDDEN_BINARIES = (
    "allure",
    "antiword",
    "chromium",
    "chromium-browser",
    "ctags",
    "fcitx5",
    "firefox",
    "fluxbox",
    "git",
    "java",
    "semgrep",
    "ssh",
    "sshpass",
    "tesseract",
    "unar",
    "websockify",
    "x11vnc",
)

FORBIDDEN_DISTRIBUTIONS = (
    "allure-pytest",
    "allure-python-commons",
    "browser-use",
    "docker",
    "playwright",
    "pytesseract",
    "selenium",
    "semgrep",
    "webdriver-manager",
)

FORBIDDEN_PATHS = (
    "/app/allure",
    "/app/deploy/release",
    "/app/local-agent-package",
    "/app/tools",
    "/ms-playwright",
    "/opt/allure",
    "/opt/schemacrawler",
    "/usr/share/novnc",
    "/var/run/docker.sock",
    "/workspace/source-repo",
)


def installed_distributions():
    return {
        str(distribution.metadata.get("Name") or "").strip().lower()
        for distribution in importlib.metadata.distributions()
    }


def main():
    distributions = installed_distributions()
    violations = {
        "binaries": {
            name: path
            for name in FORBIDDEN_BINARIES
            if (path := shutil.which(name))
        },
        "distributions": [
            name for name in FORBIDDEN_DISTRIBUTIONS if name in distributions
        ],
        "paths": [path for path in FORBIDDEN_PATHS if os.path.exists(path)],
    }
    violations = {key: value for key, value in violations.items() if value}
    payload = {
        "contract": "testhub-backend-core-v1",
        "runtime_role": os.environ.get("TESTHUB_RUNTIME_ROLE", ""),
        "status": "failed" if violations else "passed",
        "violations": violations,
    }
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
