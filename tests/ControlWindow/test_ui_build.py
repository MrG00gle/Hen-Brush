"""Tests for the Blueprint build helper. Pure Python: no gi, no real blueprint-compiler."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from ControlWindow import ui_build
from ControlWindow.ui_build import compile_blueprint, compiler_command, ensure_ui, is_stale


class FakeRunner:
    """Records command lines; can write the output file, fail, or be missing."""

    def __init__(self, returncode: int = 0, stderr: str = "", missing: bool = False) -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.missing = missing
        self.commands: List[List[str]] = []

    def __call__(self, command: List[str]) -> "subprocess.CompletedProcess[str]":
        self.commands.append(command)
        if self.missing:
            raise FileNotFoundError(command[0])
        if self.returncode == 0:
            Path(command[3]).write_text("<interface/>")
        return subprocess.CompletedProcess(command, self.returncode, stdout="", stderr=self.stderr)


@pytest.fixture
def blp(tmp_path: Path) -> Path:
    path = tmp_path / "window.blp"
    path.write_text("using Gtk 4.0;")
    return path


def set_mtime(path: Path, seconds: float) -> None:
    os.utime(path, (seconds, seconds))


class TestIsStale:
    def test_missing_ui_is_stale(self, blp, tmp_path):
        assert is_stale(blp, tmp_path / "window.ui") is True

    def test_newer_blp_is_stale(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        ui.write_text("<interface/>")
        set_mtime(ui, 1000)
        set_mtime(blp, 2000)

        assert is_stale(blp, ui) is True

    def test_newer_ui_is_fresh(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        ui.write_text("<interface/>")
        set_mtime(blp, 1000)
        set_mtime(ui, 2000)

        assert is_stale(blp, ui) is False

    def test_equally_old_ui_is_fresh(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        ui.write_text("<interface/>")
        set_mtime(blp, 1500)
        set_mtime(ui, 1500)

        assert is_stale(blp, ui) is False


class TestCompilerCommand:
    def test_defaults_to_blueprint_compiler(self, monkeypatch):
        monkeypatch.delenv(ui_build.COMPILER_ENV_VAR, raising=False)

        assert compiler_command() == "blueprint-compiler"

    def test_environment_variable_overrides_it(self, monkeypatch):
        monkeypatch.setenv(ui_build.COMPILER_ENV_VAR, "/opt/bp/blueprint-compiler")

        assert compiler_command() == "/opt/bp/blueprint-compiler"

    def test_empty_environment_variable_is_ignored(self, monkeypatch):
        monkeypatch.setenv(ui_build.COMPILER_ENV_VAR, "")

        assert compiler_command() == "blueprint-compiler"


class TestCompileBlueprint:
    def test_runs_the_compiler_with_output_and_source(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        runner = FakeRunner()

        result = compile_blueprint(blp, ui, runner=runner, compiler="bpc")

        assert result == ui
        assert runner.commands == [["bpc", "compile", "--output", str(ui), str(blp)]]
        assert ui.exists()

    def test_uses_the_environment_compiler_by_default(self, blp, tmp_path, monkeypatch):
        monkeypatch.setenv(ui_build.COMPILER_ENV_VAR, "custom-bpc")
        runner = FakeRunner()

        compile_blueprint(blp, tmp_path / "window.ui", runner=runner)

        assert runner.commands[0][0] == "custom-bpc"

    def test_missing_compiler_gives_a_clear_error(self, blp, tmp_path):
        with pytest.raises(RuntimeError) as error:
            compile_blueprint(blp, tmp_path / "window.ui", runner=FakeRunner(missing=True), compiler="bpc")

        message = str(error.value)
        assert "blueprint-compiler" in message
        assert "Install" in message
        assert ui_build.COMPILER_ENV_VAR in message

    def test_failure_includes_the_compiler_stderr(self, blp, tmp_path):
        runner = FakeRunner(returncode=1, stderr="window.blp:3:5 unexpected token\n")

        with pytest.raises(RuntimeError) as error:
            compile_blueprint(blp, tmp_path / "window.ui", runner=runner, compiler="bpc")

        assert "window.blp:3:5 unexpected token" in str(error.value)
        assert "exit code 1" in str(error.value)

    def test_failure_with_no_stderr_still_raises(self, blp, tmp_path):
        class NoStderr:
            returncode = 2
            stderr = None

        with pytest.raises(RuntimeError, match="exit code 2"):
            compile_blueprint(blp, tmp_path / "window.ui", runner=lambda command: NoStderr(), compiler="bpc")

    def test_default_runner_reports_a_missing_executable(self, blp, tmp_path):
        with pytest.raises(RuntimeError, match="blueprint-compiler"):
            compile_blueprint(blp, tmp_path / "window.ui", compiler="no-such-blueprint-compiler-xyz")

    def test_default_runner_runs_a_real_process(self, blp, tmp_path):
        completed = ui_build._run([sys.executable, "-c", "pass"])

        assert completed.returncode == 0


class TestEnsureUi:
    def test_compiles_when_the_ui_is_missing(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        runner = FakeRunner()

        assert ensure_ui(blp, ui, runner=runner, compiler="bpc") == ui
        assert len(runner.commands) == 1

    def test_does_not_compile_when_the_ui_is_fresh(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        ui.write_text("<interface/>")
        set_mtime(blp, 1000)
        set_mtime(ui, 2000)
        runner = FakeRunner()

        assert ensure_ui(blp, ui, runner=runner, compiler="bpc") == ui
        assert runner.commands == []

    def test_compiles_again_after_the_blp_changes(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        runner = FakeRunner()
        ensure_ui(blp, ui, runner=runner, compiler="bpc")
        set_mtime(ui, 1000)
        set_mtime(blp, 2000)

        ensure_ui(blp, ui, runner=runner, compiler="bpc")

        assert len(runner.commands) == 2

    def test_second_call_with_a_fresh_ui_compiles_nothing(self, blp, tmp_path):
        ui = tmp_path / "window.ui"
        runner = FakeRunner()
        set_mtime(blp, 1000)
        ensure_ui(blp, ui, runner=runner, compiler="bpc")
        set_mtime(ui, 2000)

        ensure_ui(blp, ui, runner=runner, compiler="bpc")

        assert len(runner.commands) == 1

    def test_propagates_a_compile_failure(self, blp, tmp_path):
        with pytest.raises(RuntimeError):
            ensure_ui(blp, tmp_path / "window.ui", runner=FakeRunner(missing=True), compiler="bpc")
