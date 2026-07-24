import argparse
import fnmatch
import os
import py_compile
import shutil
import tempfile
from pathlib import Path


UTF8_BOM = b"\xef\xbb\xbf"

DEFAULT_OMIT_PATTERNS = (
    "*/__pycache__/*",
    "*/tests.py",
    "*/tests/*",
)

LOCAL_AGENT_PACKAGE_FILES = (
    "local_playwright_agent.py",
    "start_local_playwright_agent.ps1",
    "start_local_playwright_agent.bat",
    "stop_local_playwright_agent.ps1",
    "stop_local_playwright_agent.bat",
    "register_local_playwright_agent.ps1",
    "testhub_agent_protocol.ps1",
    "uninstall_local_playwright_agent.ps1",
    "install_local_playwright_agent.ps1",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare source trees for PyArmor trial/protected Docker builds."
    )
    parser.add_argument("--src", required=True)
    parser.add_argument("--armor-src", required=True)
    parser.add_argument("--protected", required=True)
    parser.add_argument("--max-script-bytes", type=int, default=30000)
    parser.add_argument("--summary-file", default="")
    return parser.parse_args()


def normalize(path):
    return Path(path).as_posix()


def should_omit(relative_path):
    normalized = normalize(relative_path).lower()
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in DEFAULT_OMIT_PATTERNS)


def should_compile_to_pyc(source_path, max_script_bytes):
    if max_script_bytes <= 0:
        return False
    return source_path.stat().st_size > max_script_bytes


def copy_file(source_path, target_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)


def copy_python_file(source_path, target_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = source_path.read_bytes()
    if data.startswith(UTF8_BOM):
        target_path.write_bytes(data[len(UTF8_BOM):])
        shutil.copystat(source_path, target_path)
        return
    shutil.copy2(source_path, target_path)


def compile_legacy_pyc(source_path, target_path, relative_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    compile_source = source_path
    temp_name = None
    data = source_path.read_bytes()
    if data.startswith(UTF8_BOM):
        with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as temp_file:
            temp_file.write(data[len(UTF8_BOM):])
            temp_name = temp_file.name
        compile_source = Path(temp_name)

    py_compile.compile(
        str(compile_source),
        cfile=str(target_path),
        dfile=f"<testhub-protected>/{normalize(relative_path)}",
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    if temp_name:
        Path(temp_name).unlink(missing_ok=True)


def copy_local_agent_package_files(src, protected):
    package_dir = protected / "local-agent-package"
    for file_name in LOCAL_AGENT_PACKAGE_FILES:
        source_path = src / "tools" / file_name
        if source_path.exists() and source_path.is_file():
            copy_file(source_path, package_dir / file_name)


def reset_directory(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main():
    args = parse_args()
    src = Path(args.src).resolve()
    armor_src = Path(args.armor_src).resolve()
    protected = Path(args.protected).resolve()
    roots = ["manage.py", "backend", "apps"]

    reset_directory(armor_src)
    reset_directory(protected)

    stats = {
        "armor_py": 0,
        "pyc_py": 0,
        "non_py": 0,
        "omitted_py": 0,
    }
    pyc_paths = []

    for root_name in roots:
        root = src / root_name
        if not root.exists():
            continue

        if root.is_file():
            candidates = [root]
        else:
            candidates = [path for path in root.rglob("*") if path.is_file()]

        for source_path in candidates:
            relative_path = source_path.relative_to(src)
            if should_omit(relative_path):
                if source_path.suffix == ".py":
                    stats["omitted_py"] += 1
                continue

            if source_path.suffix != ".py":
                copy_file(source_path, protected / relative_path)
                stats["non_py"] += 1
                continue

            if should_compile_to_pyc(source_path, args.max_script_bytes):
                pyc_relative = relative_path.with_suffix(".pyc")
                compile_legacy_pyc(source_path, protected / pyc_relative, relative_path)
                stats["pyc_py"] += 1
                pyc_paths.append(normalize(relative_path))
                continue

            copy_python_file(source_path, armor_src / relative_path)
            stats["armor_py"] += 1

    copy_local_agent_package_files(src, protected)

    summary_lines = [
        f"armor_py={stats['armor_py']}",
        f"pyc_py={stats['pyc_py']}",
        f"non_py={stats['non_py']}",
        f"omitted_py={stats['omitted_py']}",
        f"max_script_bytes={args.max_script_bytes}",
    ]
    if pyc_paths:
        summary_lines.append("pyc_paths=")
        summary_lines.extend(f"  {path}" for path in sorted(pyc_paths))

    summary = "\n".join(summary_lines) + "\n"
    print(summary, end="")
    if args.summary_file:
        summary_path = Path(args.summary_file)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    main()
