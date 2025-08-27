from engine import game


def test_strip_suffix_drop(data_dir):
    g = game.Game(str(data_dir / "de" / "world.yaml"), "de")
    assert g._strip_suffix("stein ab", "ab") == "stein"


def test_strip_suffix_wear(data_dir):
    g = game.Game(str(data_dir / "de" / "world.yaml"), "de")
    assert g._strip_suffix("hut an", "an") == "hut"


def test_strip_suffix_pair(data_dir):
    g = game.Game(str(data_dir / "de" / "world.yaml"), "de")
    assert g._strip_suffix("stein fallen", "fallen") == "stein"
