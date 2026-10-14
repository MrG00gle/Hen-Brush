"""Presenter-to-GTK mapping tests. Pure Python: no gi."""

import dataclasses
from typing import Dict, List

import pytest

from ControlTower.Presenter import DronePresenter, DroneRow
from ControlWindow.row_mapping import COLUMN_KEYS, COLUMNS, RowDiff, diff_rows, excess_lines, row_values
from tests.helpers.stub_controller import StubController


def make_row(drone_id: int = 1, **changes) -> DroneRow:
    row = DroneRow(
        drone_id=drone_id,
        status="Ok",
        animation_status="Ready",
        position="0.00, 0.00, 0.00",
        position_error="0.00",
        step_text="0/5",
        step=0,
        length=5,
    )
    return dataclasses.replace(row, **changes)


def by_id(rows: List[DroneRow]) -> Dict[int, DroneRow]:
    return {row.drone_id: row for row in rows}


class TestColumns:
    def test_has_the_six_terminal_columns_in_order(self):
        assert [title for _, title in COLUMNS] == [
            "ID", "Drone Status", "Animation Status", "Position", "Pos. error", "Animation Step",
        ]

    def test_keys_are_unique(self):
        assert len(set(COLUMN_KEYS)) == len(COLUMN_KEYS) == 6

    def test_match_the_terminal_ui(self):
        from ControlTerminal.ControlTerminal import COLUMNS as TUI_COLUMNS

        assert COLUMNS == TUI_COLUMNS


class TestRowValues:
    def test_maps_every_column(self):
        row = make_row(7, status="Ok", animation_status="Live", position="1.00, 2.00, 3.00",
                       position_error="0.50", step_text="3/10", step=3, length=10)

        assert row_values(row) == {
            "id": "7",
            "status": "Ok",
            "animation_status": "Live",
            "position": "1.00, 2.00, 3.00",
            "position_error": "0.50",
            "step": "3/10",
        }

    def test_has_exactly_the_column_keys(self):
        assert list(row_values(make_row())) == list(COLUMN_KEYS)

    def test_matches_the_terminal_cells(self):
        from ControlTerminal.ControlTerminal import row_values as tui_row_values

        row = make_row(4, animation_status="Paused", step_text="2/5", step=2)

        assert tuple(row_values(row).values()) == tui_row_values(row)

    def test_maps_rows_produced_by_the_presenter(self, make_drones):
        drones = make_drones(2, 4)
        drones[1].animation_step = 2
        presenter = DronePresenter(StubController(drones))

        values = [row_values(row) for row in presenter.rows()]

        assert [value["id"] for value in values] == ["0", "1"]
        assert values[1]["step"] == "2/4"
        assert set(values[0]) == set(COLUMN_KEYS)


class TestDiffRows:
    def test_first_snapshot_is_all_added_in_order(self):
        rows = [make_row(2), make_row(5), make_row(9)]

        diff = diff_rows({}, rows)

        assert diff.added == tuple(rows)
        assert diff.changed == ()
        assert diff.removed == ()

    def test_unchanged_rows_give_an_empty_diff(self):
        rows = [make_row(1), make_row(2)]

        diff = diff_rows(by_id(rows), [make_row(1), make_row(2)])

        assert diff == RowDiff((), (), ())
        assert diff.is_empty

    @pytest.mark.parametrize("field,value", [
        ("status", "Lost"),
        ("animation_status", "Live"),
        ("position", "1.00, 0.00, 0.00"),
        ("position_error", "1.00"),
        ("step_text", "1/5"),
        ("step", 1),
    ])
    def test_one_changed_field_marks_only_that_row(self, field, value):
        previous = by_id([make_row(1), make_row(2)])
        fresh = [make_row(1), make_row(2, **{field: value})]

        diff = diff_rows(previous, fresh)

        assert diff.changed == (fresh[1],)
        assert diff.added == ()
        assert diff.removed == ()
        assert not diff.is_empty

    def test_added_drone(self):
        previous = by_id([make_row(1)])
        fresh = [make_row(1), make_row(2)]

        diff = diff_rows(previous, fresh)

        assert diff.added == (fresh[1],)
        assert diff.changed == ()

    def test_removed_drones_are_listed_ascending(self):
        previous = by_id([make_row(1), make_row(7), make_row(3)])

        diff = diff_rows(previous, [make_row(1)])

        assert diff.removed == (3, 7)
        assert diff.added == ()

    def test_added_changed_and_removed_together(self):
        previous = by_id([make_row(1), make_row(2), make_row(3)])
        fresh = [make_row(2, step=1), make_row(3), make_row(4)]

        diff = diff_rows(previous, fresh)

        assert diff.added == (fresh[2],)
        assert diff.changed == (fresh[0],)
        assert diff.removed == (1,)

    def test_keeps_input_order(self):
        previous = by_id([make_row(1), make_row(2), make_row(3)])
        fresh = [make_row(3, step=1), make_row(1, step=1), make_row(2, step=1)]

        assert [row.drone_id for row in diff_rows(previous, fresh).changed] == [3, 1, 2]

    def test_does_not_modify_the_previous_snapshot(self):
        previous = by_id([make_row(1)])

        diff_rows(previous, [make_row(1, step=3), make_row(2)])

        assert previous == by_id([make_row(1)])

    def test_empty_to_empty(self):
        assert diff_rows({}, []).is_empty


class TestExcessLines:
    @pytest.mark.parametrize("count,limit,expected", [
        (0, 10, 0),
        (10, 10, 0),
        (11, 10, 1),
        (25, 10, 15),
        (5, 1, 4),
    ])
    def test_counts_lines_over_the_limit(self, count, limit, expected):
        assert excess_lines(count, limit) == expected

    @pytest.mark.parametrize("limit", [0, -1])
    def test_rejects_a_limit_below_one(self, limit):
        with pytest.raises(ValueError):
            excess_lines(5, limit)
