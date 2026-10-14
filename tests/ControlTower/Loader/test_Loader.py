import json
import logging
from pathlib import Path

import pytest

from ControlTower.Loader import Loader
from ControlTower.common import Color, Point

CONFIG = {"serial_port": "COM3", "serial_speed": 9600, "ping_timeout": 5}
ROW = "100,1.5,2.5,3.5,10,20,30\n"


def write_csv(directory: Path, name: str, text: str = ROW) -> Path:
    path = directory / name
    path.write_text(text)
    return path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "anim"
    directory.mkdir()
    return directory


class TestConstructor:
    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="does-not-exist"):
            Loader(path=str(tmp_path / "does-not-exist"))

    def test_file_path_raises(self, tmp_path):
        file = write_csv(tmp_path, "drone_1.csv")
        with pytest.raises(NotADirectoryError, match="drone_1.csv"):
            Loader(path=str(file))

    def test_path_is_set(self, empty_dir):
        assert Loader(path=str(empty_dir)).path == empty_dir


class TestLoadConfig:
    def test_valid_config(self, animation_dir):
        directory = animation_dir(n_drones=1, config=CONFIG)
        assert Loader(str(directory)).load_config() == ("COM3", 9600, 5)

    def test_no_json_returns_none_and_warns(self, empty_dir, caplog):
        with caplog.at_level(logging.WARNING):
            assert Loader(str(empty_dir)).load_config() is None
        assert "No config file" in caplog.text

    @pytest.mark.parametrize("content", [
        "{not json",
        "",
        json.dumps({"serial_port": "COM3"}),
        json.dumps({"serial_port": "COM3", "serial_speed": "fast", "ping_timeout": 5}),
        json.dumps({"serial_port": "COM3", "serial_speed": 9600, "ping_timeout": None}),
        json.dumps(["serial_port", "serial_speed", "ping_timeout"]),
        json.dumps(5),
    ], ids=["malformed", "empty", "missing-keys", "bad-type", "null-value", "list", "number"])
    def test_bad_config_returns_none_and_logs(self, empty_dir, caplog, content):
        (empty_dir / "config.json").write_text(content)
        with caplog.at_level(logging.WARNING):
            assert Loader(str(empty_dir)).load_config() is None
        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_oserror_returns_none_and_logs(self, empty_dir, caplog, monkeypatch):
        (empty_dir / "config.json").write_text(json.dumps(CONFIG))

        def boom(self, *args, **kwargs):
            raise OSError("denied")

        monkeypatch.setattr(Path, "open", boom)
        with caplog.at_level(logging.WARNING):
            assert Loader(str(empty_dir)).load_config() is None
        assert "config.json" in caplog.text

    def test_two_json_files_first_sorted_wins_with_warning(self, empty_dir, caplog):
        (empty_dir / "b.json").write_text(json.dumps({**CONFIG, "serial_port": "COM9"}))
        (empty_dir / "a.json").write_text(json.dumps(CONFIG))
        with caplog.at_level(logging.WARNING):
            assert Loader(str(empty_dir)).load_config() == ("COM3", 9600, 5)
        assert "a.json" in caplog.text


class TestLoad:
    def test_without_config(self, animation_dir):
        directory = animation_dir(n_drones=2)
        port, speed, timeout, drones = Loader(str(directory)).load()
        assert (port, speed, timeout) == (None, None, None)
        assert [d.id for d in drones] == [0, 1]

    def test_with_config(self, animation_dir):
        directory = animation_dir(n_drones=2, config=CONFIG)
        assert Loader(str(directory)).load()[:3] == ("COM3", 9600, 5)

    def test_empty_directory(self, empty_dir):
        assert Loader(str(empty_dir)).load() == (None, None, None, [])


class TestLoadDrones:
    @pytest.mark.parametrize("name, expected", [
        ("drone_3.csv", 3),
        ("Drone7.csv", 7),
        ("DRONE_08.csv", 8),
        ("12.csv", 12),
    ])
    def test_id_is_numeric_part_as_int(self, empty_dir, name, expected):
        write_csv(empty_dir, name)
        drones = Loader(str(empty_dir)).load_drones()
        assert [d.id for d in drones] == [expected]
        assert type(drones[0].id) is int

    @pytest.mark.parametrize("name", ["drone_a.csv", "drone_1.txt", "x.csv", "drone_.csv", "mydrone_1.csv"])
    def test_non_matching_names_ignored(self, empty_dir, name):
        write_csv(empty_dir, name)
        assert Loader(str(empty_dir)).load_drones() == []

    def test_sorted_by_id(self, empty_dir):
        for name in ("drone_10.csv", "drone_2.csv", "drone_1.csv"):
            write_csv(empty_dir, name)
        assert [d.id for d in Loader(str(empty_dir)).load_drones()] == [1, 2, 10]

    def test_duplicate_id_skips_second_with_error(self, empty_dir, caplog):
        write_csv(empty_dir, "drone_1.csv", "100,1,1,1,1,1,1\n")
        write_csv(empty_dir, "1.csv", "200,2,2,2,2,2,2\n")
        with caplog.at_level(logging.ERROR):
            drones = Loader(str(empty_dir)).load_drones()
        assert len(drones) == 1
        # Files are read in sorted name order, so "1.csv" comes first and "drone_1.csv" is the duplicate.
        assert drones[0].animation.timestamps == [200]
        assert "drone_1.csv" in caplog.text

    def test_id_over_255_skipped_with_error(self, empty_dir, caplog):
        write_csv(empty_dir, "drone_256.csv")
        write_csv(empty_dir, "drone_255.csv")
        with caplog.at_level(logging.ERROR):
            drones = Loader(str(empty_dir)).load_drones()
        assert [d.id for d in drones] == [255]
        assert "drone_256.csv" in caplog.text

    @pytest.mark.parametrize("bad_row", [
        "1,2,3\n",
        "abc,1,2,3,4,5,6\n",
        "100,1,2,3,4,5,x\n",
        "ts,x,y,z,r,g,b\n",
    ], ids=["short", "non-numeric", "bad-color", "header"])
    def test_bad_row_skipped_others_kept(self, empty_dir, caplog, bad_row):
        write_csv(empty_dir, "drone_1.csv", "100,0,0,0,1,2,3\n" + bad_row + "300,1,1,1,4,5,6\n")
        with caplog.at_level(logging.WARNING):
            drones = Loader(str(empty_dir)).load_drones()
        assert drones[0].animation.timestamps == [100, 300]
        assert "drone_1.csv" in caplog.text
        assert "line 2" in caplog.text

    def test_blank_line_skipped_with_log(self, empty_dir, caplog):
        write_csv(empty_dir, "drone_1.csv", "100,0,0,0,1,2,3\n\n300,1,1,1,4,5,6\n")
        with caplog.at_level(logging.WARNING):
            drones = Loader(str(empty_dir)).load_drones()
        assert drones[0].animation.timestamps == [100, 300]
        assert "line 2" in caplog.text

    def test_file_without_valid_rows_skipped(self, empty_dir, caplog):
        write_csv(empty_dir, "drone_1.csv", "garbage\n")
        write_csv(empty_dir, "drone_2.csv")
        with caplog.at_level(logging.WARNING):
            drones = Loader(str(empty_dir)).load_drones()
        assert [d.id for d in drones] == [2]
        assert "drone_1.csv" in caplog.text

    def test_unreadable_file_skipped(self, empty_dir, caplog, monkeypatch):
        write_csv(empty_dir, "drone_1.csv")
        real_open = open

        def boom(file, *args, **kwargs):
            if str(file).endswith("drone_1.csv"):
                raise OSError("denied")
            return real_open(file, *args, **kwargs)

        monkeypatch.setattr("builtins.open", boom)
        monkeypatch.setattr(Path, "open", lambda self, *a, **k: boom(self, *a, **k))
        with caplog.at_level(logging.ERROR):
            assert Loader(str(empty_dir)).load_drones() == []
        assert "drone_1.csv" in caplog.text

    def test_animation_content(self, empty_dir):
        path = write_csv(empty_dir, "drone_4.csv", "0,1.5,2.5,3.5,10,20,30\n500,4,5,6,40,50,60\n")
        animation = Loader(str(empty_dir)).load_drones()[0].animation
        assert animation.timestamps == [0, 500]
        assert animation.flight_path == [Point(1.5, 2.5, 3.5), Point(4.0, 5.0, 6.0)]
        assert animation.colors == [Color(10, 20, 30), Color(40, 50, 60)]
        assert animation.path == path
