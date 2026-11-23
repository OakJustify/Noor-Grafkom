from nur_game.state import Lantern, Memory, Narrative


def test_lantern_capacity_falls_in_quarters_never_back():
    lantern = Lantern()
    assert lantern.capacity == 1.0
    expected = (0.75, 0.5, 0.25, 0.0)
    for capacity in expected:
        lantern.collect_fragment()
        assert lantern.capacity == capacity
        assert lantern.charge <= capacity
        lantern.step(120.0)
        assert lantern.charge >= 0.0
    assert lantern.capacity == 0.0


def test_death_costs_charge_but_not_capacity():
    lantern = Lantern()
    lantern.collect_fragment()
    before = lantern.snapshot()
    lantern.die()
    after = lantern.snapshot()
    assert after["capacity"] == before["capacity"]
    assert after["charge"] < before["charge"]


def test_memory_candle_restores_meaning_without_touching_light():
    memory = Memory()
    lantern = Lantern()
    memory.add("key", false=True)
    before = lantern.snapshot()
    assert memory.gain_candle() is True
    assert memory.gain_candle() is False
    assert memory.restore() is True
    assert memory.truth == 1
    assert "key" not in memory.false
    assert lantern.snapshot() == before


def test_narrative_is_seeded_and_keeps_anchor_order():
    def run():
        narrative = Narrative(99)
        lines = []
        for _ in range(900):
            line = narrative.update(1 / 60, 0.4, 1)
            if line:
                lines.append(line)
        return lines

    first, second = run(), run()
    assert first == second
    assert first[:3] == [
        "Rumah ini lebih sunyi dari biasanya.",
        "sepertinya kamu lupa menutup pintu",
        "kau membunuhku!",
    ]
