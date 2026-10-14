"""Compile Blueprint (``.blp``) files to GTK builder XML (``.ui``) when the ``.ui`` is out of date.

This module is pure Python and does not import ``gi``, so it can be tested anywhere.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

COMPILER_ENV_VAR = "BLUEPRINT_COMPILER"
DEFAULT_COMPILER = "blueprint-compiler"
INSTALL_HINT = (
    "Install blueprint-compiler (Debian/Ubuntu: 'sudo apt install blueprint-compiler', "
    "Fedora: 'sudo dnf install blueprint-compiler', Arch: 'sudo pacman -S blueprint-compiler') "
    f"or point the {COMPILER_ENV_VAR} environment variable at the executable."
)

# Takes the full command line and returns an object with ``returncode`` and ``stderr``
# (a ``subprocess.CompletedProcess`` satisfies this). Injected by tests.
Runner = Callable[[List[str]], "subprocess.CompletedProcess[str]"]


def _run(command: List[str]) -> "subprocess.CompletedProcess[str]":
    """Default runner: run the command and capture its output as text."""
    return subprocess.run(command, check=False, capture_output=True, text=True)


def compiler_command() -> str:
    """Executable used to compile Blueprint files: ``$BLUEPRINT_COMPILER`` or ``blueprint-compiler``."""
    return os.environ.get(COMPILER_ENV_VAR) or DEFAULT_COMPILER


def is_stale(blp: Path, ui: Path) -> bool:
    """Whether ``ui`` has to be (re)built from ``blp``.

    Args:
        blp: Blueprint source file.
        ui: Compiled builder file.

    Returns:
        True if ``ui`` does not exist or is older than ``blp``; False if it is newer or equally old.
    """
    if not ui.exists():
        return True
    return blp.stat().st_mtime > ui.stat().st_mtime


def compile_blueprint(blp: Path, ui: Path, runner: Optional[Runner] = None, compiler: Optional[str] = None) -> Path:
    """Run ``blueprint-compiler compile --output <ui> <blp>``.

    Args:
        blp: Blueprint source file.
        ui: Where to write the compiled builder file.
        runner: Runs the command line; defaults to ``subprocess.run`` with captured text output.
        compiler: Compiler executable; defaults to ``compiler_command()``.

    Returns:
        The path of the compiled file (``ui``).

    Raises:
        RuntimeError: If the compiler can't be started, or exits with a non-zero code. The message
            then includes the compiler's stderr.
    """
    run = runner if runner is not None else _run
    executable = compiler if compiler is not None else compiler_command()
    command = [executable, "compile", "--output", str(ui), str(blp)]

    logger.info("Compiling %s -> %s", blp, ui)
    try:
        completed = run(command)
    except FileNotFoundError as error:
        raise RuntimeError(f"Cannot run '{executable}' to compile {blp.name}. {INSTALL_HINT}") from error

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(f"'{executable}' failed with exit code {completed.returncode} for {blp}:\n{stderr}")
    return ui


def ensure_ui(blp: Path, ui: Path, runner: Optional[Runner] = None, compiler: Optional[str] = None) -> Path:
    """Compile ``blp`` into ``ui`` only if ``ui`` is stale.

    Args:
        blp: Blueprint source file.
        ui: Compiled builder file.
        runner: See ``compile_blueprint``.
        compiler: See ``compile_blueprint``.

    Returns:
        The path of the up-to-date ``ui`` file.

    Raises:
        RuntimeError: If a compile was needed and failed.
    """
    if is_stale(blp, ui):
        compile_blueprint(blp, ui, runner=runner, compiler=compiler)
    return ui
