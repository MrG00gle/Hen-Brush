"""Tests for the ``python -m ControlWindow`` entry point. The GTK application is replaced by a fake."""

import importlib
import logging
from pathlib import Path

import pytest

SAMPLE_ANIMATION = Path(__file__).resolve().parents[2] / "sample_animation"

main_module = importlib.import_module("ControlWindow.__main__")
build_parser = main_module.build_parser
main = main_module.main


class FakeApplication:
    """Stands in for HenBrushApplication: records its arguments and returns from ``run`` at once."""

    instances = []
    status = 0

    def __init__(self, presenter, log_buffer, shutdown=None):
        self.presenter = presenter
        self.log_buffer = log_buffer
        self.shutdown = shutdown
        self.run_argv = None
        FakeApplication.instances.append(self)

    def run(self, argv):
        self.run_argv = argv
        return FakeApplication.status


@pytest.fixture
def fake_application(monkeypatch):
    FakeApplication.instances = []
    FakeApplication.status = 0
    monkeypatch.setattr(main_module, "_load_application", lambda: FakeApplication)
    return FakeApplication


class TestParser:
    def test_accepts_the_animation_dir_and_options(self):
        args = build_parser().parse_args(["anim", "--port", "loop://", "--speed", "115200", "--timeout", "1"])

        assert (args.animation_dir, args.port, args.speed, args.timeout) == ("anim", "loop://", 115200, 1.0)

    def test_missing_animation_dir_exits_with_code_2(self, capsys):
        with pytest.raises(SystemExit) as exit_info:
            build_parser().parse_args([])

        assert exit_info.value.code == 2
        assert "animation_dir" in capsys.readouterr().err


class TestMain:
    def test_runs_the_application_on_the_presenter_and_cleans_up(self, fake_application, animation_dir):
        directory = animation_dir(n_drones=2, frames=3)
        handlers_before = list(logging.getLogger().handlers)

        code = main([str(directory), "--port", "loop://", "--speed", "115200", "--timeout", "0.1"])

        assert code == 0
        (app,) = fake_application.instances
        assert app.run_argv == []
        assert [row.drone_id for row in app.presenter.rows()] == [0, 1]
        assert logging.getLogger().handlers == handlers_before

    def test_returns_the_application_exit_status(self, fake_application, animation_dir):
        fake_application.status = 3

        code = main([str(animation_dir()), "--port", "loop://", "--speed", "115200", "--timeout", "0.1"])

        assert code == 3

    def test_missing_directory_returns_2_with_a_one_line_message(self, fake_application, tmp_path, capsys):
        code = main([str(tmp_path / "nope"), "--port", "loop://", "--speed", "1", "--timeout", "1"])

        captured = capsys.readouterr()
        assert code == 2
        assert fake_application.instances == []
        assert len(captured.err.strip().splitlines()) == 1
        assert "nope" in captured.err
        assert "Traceback" not in captured.err

    def test_missing_serial_config_returns_2(self, fake_application, animation_dir, capsys):
        code = main([str(animation_dir())])

        assert code == 2
        assert "serial" in capsys.readouterr().err.lower()

    def test_bundled_sample_animation_loads(self, fake_application):
        code = main([str(SAMPLE_ANIMATION)])

        assert code == 0
        (app,) = fake_application.instances
        assert len(app.presenter.rows()) == 3

    @pytest.mark.parametrize("error", [ImportError("No module named 'gi'"), ValueError("Namespace Adw not available"),
                                       RuntimeError("blueprint-compiler missing")])
    def test_unavailable_gtk_returns_1_before_opening_the_serial_port(self, monkeypatch, tmp_path, capsys, error):
        def fail():
            raise error

        monkeypatch.setattr(main_module, "_load_application", fail)
        created = []
        monkeypatch.setattr(main_module, "create_presenter", lambda args: created.append(args))

        code = main([str(tmp_path), "--port", "loop://"])

        captured = capsys.readouterr()
        assert code == 1
        assert created == []
        assert "not available" in captured.err
        assert "Traceback" not in captured.err
