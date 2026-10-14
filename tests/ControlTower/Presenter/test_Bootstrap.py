import argparse
import logging

import pytest

from ControlTower import ControlTower
from ControlTower.Presenter import DronePresenter, LogBuffer, add_connection_arguments, create_presenter
from ControlTower.common import SerialConfigLoadFailed


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    add_connection_arguments(parser)
    return parser


class TestArguments:
    def test_parses_all_options(self, parser):
        args = parser.parse_args(["some/dir", "--port", "COM3", "--speed", "115200", "--timeout", "0.5"])
        assert (args.animation_dir, args.port, args.speed, args.timeout) == ("some/dir", "COM3", 115200, 0.5)

    def test_options_are_optional(self, parser):
        args = parser.parse_args(["some/dir"])
        assert (args.port, args.speed, args.timeout) == (None, None, None)

    def test_animation_dir_is_required(self, parser):
        with pytest.raises(SystemExit) as exit_info:
            parser.parse_args([])
        assert exit_info.value.code == 2

    def test_speed_must_be_an_integer(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["some/dir", "--speed", "fast"])


class TestCreatePresenter:
    @pytest.fixture
    def created(self, parser, animation_dir):
        directory = animation_dir(n_drones=3, frames=4)
        args = parser.parse_args([str(directory), "--port", "loop://", "--speed", "115200", "--timeout", "0.1"])
        tower, presenter, log_buffer = create_presenter(args)
        yield tower, presenter, log_buffer
        log_buffer.uninstall()
        tower.shutdown()

    def test_builds_connected_parts(self, created):
        tower, presenter, log_buffer = created
        assert isinstance(tower, ControlTower)
        assert isinstance(presenter, DronePresenter)
        assert isinstance(log_buffer, LogBuffer)
        assert [row.drone_id for row in presenter.rows()] == [0, 1, 2]
        assert all(row.step_text == "0/4" for row in presenter.rows())

    def test_log_buffer_is_installed_on_the_root_logger(self, created):
        _, _, log_buffer = created
        assert log_buffer in logging.getLogger().handlers

        logging.getLogger("tests.bootstrap").info("from the app")

        assert "from the app" in [entry.message for entry in log_buffer.entries()]

    def test_serial_config_may_come_from_the_json_file(self, parser, animation_dir):
        directory = animation_dir(config={"serial_port": "loop://", "serial_speed": 9600, "ping_timeout": 1})
        tower, _, log_buffer = create_presenter(parser.parse_args([str(directory)]))
        log_buffer.uninstall()
        tower.shutdown()

    def test_missing_serial_config_raises_and_leaves_no_handler_behind(self, parser, animation_dir):
        directory = animation_dir()
        handlers_before = list(logging.getLogger().handlers)

        with pytest.raises(SerialConfigLoadFailed):
            create_presenter(parser.parse_args([str(directory)]))

        assert logging.getLogger().handlers == handlers_before

    def test_missing_directory_raises(self, parser, tmp_path):
        with pytest.raises(FileNotFoundError):
            create_presenter(parser.parse_args([str(tmp_path / "nope"), "--port", "loop://", "--speed", "1", "--timeout", "1"]))
