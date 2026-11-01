from letrasiq.spec import FontSpec


def test_default_spec_valid():
    spec = FontSpec(name="letra-sans")
    assert spec.validate() == []
    assert spec.family_name() == "Letra Sans"


def test_spec_roundtrip(tmp_path):
    spec = FontSpec(name="demo", x_height=520, mood="crisp")
    path = tmp_path / "spec.json"
    spec.save(path)
    loaded = FontSpec.load(path)
    assert loaded.x_height == 520
    assert loaded.mood == "crisp"
