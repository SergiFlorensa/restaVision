from __future__ import annotations

from tools.run_table_occupancy_baseline import OccupancyState, update_occupancy_state


def test_occupancy_baseline_confirms_occupied_after_delay(capsys) -> None:
    state = OccupancyState()

    update_occupancy_state(
        state, 1, now=10.0, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )
    update_occupancy_state(
        state, 1, now=12.0, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )
    update_occupancy_state(
        state, 1, now=13.1, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )

    assert state.state == "occupied"
    assert "OCUPADA" in capsys.readouterr().out


def test_occupancy_baseline_confirms_free_after_delay(capsys) -> None:
    state = OccupancyState(state="occupied")

    update_occupancy_state(
        state, 0, now=20.0, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )
    update_occupancy_state(
        state, 0, now=24.0, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )
    update_occupancy_state(
        state, 0, now=25.1, occupied_seconds=3.0, free_seconds=5.0, table_id="m1"
    )

    assert state.state == "free"
    assert "LIBRE" in capsys.readouterr().out
