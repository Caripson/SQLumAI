import importlib


def test_rules_crud(tmp_path, monkeypatch):
    rules_path = tmp_path / "rules.json"
    monkeypatch.setenv("RULES_PATH", str(rules_path))

    # Import after setting env so RULES_PATH is picked up
    api = importlib.import_module("src.api")
    importlib.reload(api)

    # List empty
    assert api.list_rules() == []

    # Add rule
    rule = api.Rule(
        id="r1",
        target="column",
        selector="dbo.Customers.Phone",
        action="autocorrect",
        reason="Normalize SE phone",
        confidence=0.9,
    )
    added = api.add_rule(rule)
    assert added.id == "r1"

    # List again
    assert len(api.list_rules()) == 1

    # Delete
    resp = api.delete_rule("r1")
    assert resp["deleted"] == "r1"
