from src.policy.engine import PolicyEngine, Rule, Event


def test_policy_matches_and_env():
    rules = [
        Rule(id='r1', target='table', selector='dbo.T', action='block', reason='nope', enabled=True, confidence=1.0),
        Rule(id='r2', target='column', selector='Email', action='autocorrect', reason='fix', enabled=True, confidence=0.9, ),
        Rule(id='r3', target='pattern', selector='insert into t', action='allow', reason='ok', enabled=False, confidence=1.0),
        Rule(id='r4', target='column', selector='dbo.U.Phone', action='autocorrect', reason='phone', enabled=True, confidence=0.9, ),
    ]
    eng = PolicyEngine(rules, environment='dev')
    d = eng.decide(Event(database=None, user=None, sql_text=None, table='dbo.T', column=None, value=None))
    assert d.action == 'block' and d.rule_id == 'r1'
    d2 = eng.decide(Event(database=None, user=None, sql_text=None, table=None, column='dbo.U.Phone', value='0701'))
    assert d2.action == 'autocorrect' and d2.rule_id == 'r4'
    d3 = eng.decide(Event(database=None, user=None, sql_text=None, table=None, column='Email', value='x'))
    assert d3.action == 'autocorrect'
