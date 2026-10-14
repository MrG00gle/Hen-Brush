def test_discovery_and_imports():
    import ControlTower.common

    assert ControlTower.common.Point is not None


def test_factories_available(make_drones, animation_dir, tmp_path):
    drones = make_drones(num_drones=3, anim_length=4)
    assert [d.id for d in drones] == [0, 1, 2]
    assert all(len(d.animation) == 4 for d in drones)
    assert all(tmp_path in d.animation.path.parents for d in drones)

    directory = animation_dir(n_drones=2, frames=3)
    assert len(list(directory.glob("*.csv"))) == 2
