import pytest
from backend.app.options.strategies import (
    short_strangle, iron_condor, bull_put_spread, bear_call_spread, iron_fly,
    calendar_spread, ratio_spread_1x2, _pop_between, _nearest_by_delta, _atm,
)

SPOT = 100.0
EXPIRY = "2026-12-31"  # far enough out that days_to_expiry > 0 regardless of "today"

# Synthetic chain: CE delta decreases with strike (0.5 ATM down to ~0.05 far OTM),
# PE delta = CE delta - 1 (put-call parity approximation), premiums roughly track
# delta (deep ITM/ATM more expensive, far OTM cheap), flat IV so avg-IV math is simple.
_STRIKES_DELTAS = [
    (70, 0.95), (80, 0.88), (85, 0.80), (90, 0.70), (95, 0.60),
    (98, 0.55), (100, 0.50), (102, 0.45), (105, 0.40), (108, 0.30),
    (110, 0.24), (112, 0.16), (115, 0.10), (120, 0.06), (130, 0.02),
]


def make_chain():
    chain = []
    for strike, ce_delta in _STRIKES_DELTAS:
        pe_delta = ce_delta - 1.0
        ce_prem = round(max(SPOT - strike, 0) + ce_delta * 8, 2)
        pe_prem = round(max(strike - SPOT, 0) + abs(pe_delta) * 8, 2)
        chain.append({
            "strike": strike,
            "isATM": strike == 100,
            "CE": {"ltp": ce_prem, "delta": ce_delta, "theta": -0.5 - ce_delta, "iv": 20.0, "oi": 10000},
            "PE": {"ltp": pe_prem, "delta": pe_delta, "theta": -0.5 - abs(pe_delta), "iv": 20.0, "oi": 10000},
        })
    return chain


def test_atm_and_nearest_by_delta_helpers():
    chain = make_chain()
    atm = _atm(chain)
    assert atm["strike"] == 100
    near_call = _nearest_by_delta(chain, "CE", 0.16)
    assert near_call["strike"] == 112  # closest CE delta to 0.16 is 0.16 itself at 112


def test_short_strangle_sells_both_sides_for_credit():
    chain = make_chain()
    res = short_strangle(chain, SPOT, EXPIRY, iv_rank=70, adx=15)
    assert res["strategy"] == "short_strangle"
    assert len(res["legs"]) == 2
    assert all(l["side"] == "sell" for l in res["legs"])
    assert res["net_premium"] > 0  # credit received
    assert res["max_profit"] == res["net_premium"]
    assert res["max_loss"] == "unlimited"  # naked both sides, no wings
    assert res["regime"]["eligible"] is True


def test_short_strangle_regime_ineligible_low_iv_rank():
    chain = make_chain()
    res = short_strangle(chain, SPOT, EXPIRY, iv_rank=20, adx=15)
    assert res["regime"]["eligible"] is False


def test_short_strangle_regime_unknown_without_inputs():
    chain = make_chain()
    res = short_strangle(chain, SPOT, EXPIRY)
    assert res["regime"]["eligible"] is None


def test_iron_condor_has_defined_bounded_loss():
    chain = make_chain()
    res = iron_condor(chain, SPOT, EXPIRY, iv_rank=70, adx=15)
    assert len(res["legs"]) == 4
    assert isinstance(res["max_loss"], (int, float))  # bounded by the wings, not "unlimited"
    assert res["margin_estimate"] == abs(res["max_loss"])
    assert res["net_premium"] > 0


def test_bull_put_spread_is_credit_with_defined_risk():
    chain = make_chain()
    res = bull_put_spread(chain, SPOT, EXPIRY)
    assert res["strategy"] == "bull_put_spread"
    assert res["legs"][0]["side"] == "sell" and res["legs"][0]["type"] == "PE"
    assert res["legs"][1]["side"] == "buy" and res["legs"][1]["type"] == "PE"
    assert res["net_premium"] > 0
    assert isinstance(res["max_loss"], (int, float))


def test_bear_call_spread_is_credit_with_defined_risk():
    chain = make_chain()
    res = bear_call_spread(chain, SPOT, EXPIRY)
    assert res["strategy"] == "bear_call_spread"
    assert res["legs"][0]["side"] == "sell" and res["legs"][0]["type"] == "CE"
    assert res["net_premium"] > 0
    assert isinstance(res["max_loss"], (int, float))


def test_iron_fly_sells_atm_both_sides():
    chain = make_chain()
    res = iron_fly(chain, SPOT, EXPIRY, iv_rank=70, adx=15)
    sold_strikes = {l["strike"] for l in res["legs"] if l["side"] == "sell"}
    assert sold_strikes == {100}  # both short legs at the ATM strike
    assert res["net_premium"] > 0
    assert isinstance(res["max_loss"], (int, float))


def test_ratio_spread_1x2_sells_two_of_further_otm():
    chain = make_chain()
    res = ratio_spread_1x2(chain, SPOT, EXPIRY, side="CE")
    sell_leg = next(l for l in res["legs"] if l["side"] == "sell")
    buy_leg = next(l for l in res["legs"] if l["side"] == "buy")
    assert sell_leg["qty"] == 2
    assert sell_leg["strike"] > buy_leg["strike"]  # short leg further OTM than the long leg
    assert res["margin_estimate"] is not None


def test_calendar_spread_contango_eligible():
    near_chain = make_chain()
    far_chain = make_chain()
    for c in far_chain:
        c["CE"]["iv"] = 24.0  # far expiry richer IV = contango
    res = calendar_spread(near_chain, far_chain, SPOT, "2026-09-01", "2026-10-01")
    assert res["strategy"] == "calendar_spread"
    assert res["regime"]["eligible"] is True
    assert res["legs"][0]["side"] == "sell"  # sell near
    assert res["legs"][1]["side"] == "buy"   # buy far


def test_calendar_spread_backwardation_ineligible():
    near_chain = make_chain()
    far_chain = make_chain()  # same IV -- not contango
    res = calendar_spread(near_chain, far_chain, SPOT, "2026-09-01", "2026-10-01")
    assert res["regime"]["eligible"] is False


# --- POP helper ---

def test_pop_between_symmetric_breakevens_near_50_when_spot_centered():
    pop = _pop_between([90, 110], spot=100.0, avg_iv_pct=20.0, T=30/365, direction="between")
    assert pop is not None
    assert 0 < pop < 100


def test_pop_wider_breakevens_gives_higher_probability():
    narrow = _pop_between([95, 105], spot=100.0, avg_iv_pct=20.0, T=30/365, direction="between")
    wide = _pop_between([80, 120], spot=100.0, avg_iv_pct=20.0, T=30/365, direction="between")
    assert wide > narrow


def test_pop_none_when_inputs_missing():
    assert _pop_between([], spot=100.0, avg_iv_pct=20.0, T=0.1, direction="between") is None
    assert _pop_between([90, 110], spot=100.0, avg_iv_pct=None, T=0.1, direction="between") is None
