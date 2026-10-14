"""Tests for the ``python -m ControlTerminal`` entry point (the app itself is replaced by a fake)."""

import importlib
import logging
from pathlib import Path

import pytest

SAMPLE_ANIMATION = Path(__file__).resolve().parents[2] / "sample_animation"

main_module = importlib.import_module("ControlTerminal.__main__")
build_parser = main_module.build_parser
main = main_module.main


class FakeApp:
    """Stands in for ControlTerminal: records its arguments and returns from ``run`` at once."""

    instances = []

    def __init__(self, presenter, log_buffer, refresh_interval=0.25, shutdown=None, **kwargs):
        self.presenter = presenter
        self.log_buffer = log_buffer
        self.refresh_interval = refresh_interval
        self.shutdown = shutdown
        self.ran = False
        FakeApp.instances.append(self)

    def run(self):
        self.ran = True


@pytest.fixture
def fake_app(monkeypatch):
    FakeApp.instances = []
    monkeypatch.setattr(main_module, "ControlTerminal", FakeApp)
    return FakeApp


class TestParser:
    def test_accepts_the_animation_dir_and_options(self):
        args = build_parser().parse_args(["anim", "--port", "loop://", "--speed", "115200", "--timeout", "1", "--refresh", "0.5"])

        assert (args.animation_dir, args.port, args.speed, args.timeout, args.refresh) == ("anim", "loop://", 115200, 1.0, 0.5)

    def test_refresh_defaults_to_a_quarter_second(self):
        assert build_parser().parse_args(["anim"]).refresh == 0.25

    def test_missing_animation_dir_exits_with_code_2(self, capsys):
        with pytest.raises(SystemExit) as exit_info:
            build_parser().parse_args([])

        assert exit_info.value.code == 2
        assert "animation_dir" in capsys.readouterr().err

    def test_main_without_arguments_exits_with_code_2(self):
        with pytest.raises(SystemExit) as exit_info:
            main([])

        assert exit_info.value.code == 2

    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_refresh_must_be_positive(self, value):
        with pytest.raises(SystemExit) as exit_info:
            main(["anim", "--refresh", value])

        assert exit_info.value.code == 2


class TestMain:
    def test_runs_the_app_on_the_presenter_and_cleans_up(self, fake_app, animation_dir):
        directory = animation_dir(n_drones=2, frames=3)
        handlers_before = list(logging.getLogger().handlers)

        code = main([str(directory), "--port", "loop://", "--speed", "115200", "--timeout", "0.1", "--refresh", "0.1"])

        assert code == 0
        (app,) = fake_app.instances
        assert app.ran
        assert app.refresh_interval == 0.1
        assert [row.drone_id for row in app.presenter.rows()] == [0, 1]
        assert logging.getLogger().handlers == handlers_before
        app.shutdown()

    def test_missing_directory_returns_2_with_a_one_line_message(self, fake_app, tmp_path, capsys):
        code = main([str(tmp_path / "nope"), "--port", "loop://", "--speed", "1", "--timeout", "1"])

        captured = capsys.readouterr()
        assert code == 2
        assert fake_app.instances == []
        assert len(captured.err.strip().splitlines()) == 1
        assert "nope" in captured.err
        assert "Traceback" not in captured.err

    def test_missing_serial_config_returns_2(self, fake_app, animation_dir, capsys):
        code = main([str(animation_dir())])

        assert code == 2
        assert "serial" in capsys.readouterr().err.lower()

    def test_unusable_serial_port_returns_2(self, fake_app, animation_dir, capsys):
        code = main([str(animation_dir()), "--port", "no-such-port-xyz", "--speed", "9600", "--timeout", "1"])

        assert code == 2
        assert fake_app.instances == []
        assert "Traceback" not in capsys.readouterr().err

    def test_bundled_sample_animation_loads(self, fake_app, capsys):
        code = main([str(SAMPLE_ANIMATION)])

        assert code == 0
        (app,) = fake_app.instances
        assert len(app.presenter.rows()) == 3
        app.shutdown()
