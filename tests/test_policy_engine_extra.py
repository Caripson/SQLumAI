from src.policy.engine import PolicyEngine, Rule, Event


def test_environment_scoping_and_pattern_and_get_rule():
    rules = [
        Rule(id="env-only", target="table", selector="dbo.T", action="block"),
        Rule(id="prod-rule", target="pattern", selector="insert into accounts", action="block"),
    ]
    # Attach apply_in_envs dynamically (allowed in engine via getattr)
    setattr(rules[1], "apply_in_envs", ["prod"])  # pattern rule applies only in prod

    # In dev environment, pattern rule should be skipped
    eng_dev = PolicyEngine(rules, environment="dev")
    d1 = eng_dev.decide(Event(database=None, user=None, sql_text="insert into accounts ...", table=None, column=None, value=None))
    # No table match nor allowed pattern due to env -> default allow
    assert d1.action == "allow" and d1.rule_id is None

    # In prod environment, pattern rule matches
    eng_prod = PolicyEngine(rules, environment="prod")
    d2 = eng_prod.decide(Event(database=None, user=None, sql_text="INSERT INTO Accounts values (...)", table=None, column=None, value=None))
    assert d2.action == "block" and d2.rule_id == "prod-rule"

    # get_rule helper
    assert eng_prod.get_rule("prod-rule").id == "prod-rule"  # type: ignore[union-attr]
    assert eng_prod.get_rule(None) is None

