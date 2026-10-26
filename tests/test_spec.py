from letrasiq.spec import FontSpec


def test_default_spec_valid():
    spec = FontSpec(name="letra-sans")
    assert spec.validate() == []
    assert spec.family_name() == "Letra Sans"
    assert spec.stroke_base() > 0


def test_spec_roundtrip(tmp_path):
    spec = FontSpec(name="demo", weight=0.5, mood="crisp")
    path = tmp_path / "spec.json"
    spec.save(path)
    loaded = FontSpec.load(path)
    assert loaded.weight == 0.5
    assert loaded.mood == "crisp"