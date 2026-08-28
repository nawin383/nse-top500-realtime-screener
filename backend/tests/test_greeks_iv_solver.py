from backend.app.options.greeks import black_scholes_greeks, implied_volatility


def test_iv_round_trip_call():
    # Price a call at a known IV, then invert the price back to IV -- should
    # recover (approximately) the same value. This is the actual mechanism
    # fetcher_kite.py relies on since Kite's /quote gives LTP but not IV.
    spot, strike, T, r = 24500.0, 24600.0, 20 / 365, 0.06
    true_iv = 0.18
    price = black_scholes_greeks(spot, strike, T, true_iv, r, "CE")["price"]
    solved = implied_volatility(price, spot, strike, T, r, "CE")
    assert solved is not None
    assert abs(solved - true_iv) < 0.001


def test_iv_round_trip_put():
    spot, strike, T, r = 100.0, 95.0, 30 / 365, 0.06
    true_iv = 0.32
    price = black_scholes_greeks(spot, strike, T, true_iv, r, "PE")["price"]
    solved = implied_volatility(price, spot, strike, T, r, "PE")
    assert solved is not None
    assert abs(solved - true_iv) < 0.001


def test_iv_round_trip_otm_low_vega():
    # OTM with low vega (where Newton-Raphson would be unstable) -- confirmed
    # by hand that this price (0.17) is meaningfully above the practical
    # price floor (0.05 at near-zero vol), so the IV is still identifiable;
    # this is exactly why bisection, not Newton, is used here.
    spot, strike, T, r = 100.0, 120.0, 30 / 365, 0.06
    true_iv = 0.35
    price = black_scholes_greeks(spot, strike, T, true_iv, r, "CE")["price"]
    solved = implied_volatility(price, spot, strike, T, r, "CE")
    assert solved is not None
    assert abs(solved - true_iv) < 0.01


def test_iv_returns_floor_when_price_at_practical_minimum():
    # A genuinely degenerate case: so deep OTM / so little time that the
    # theoretical price is clamped to the 0.05 floor at every vol from ~0 up
    # to a very high one. Many IVs could produce that same floor price, so
    # recovering "the" true IV is ill-posed -- the solver correctly returns
    # the low end of its bracket rather than guessing, and must not raise.
    spot, strike, T, r = 100.0, 150.0, 10 / 365, 0.06
    price = black_scholes_greeks(spot, strike, T, 0.45, r, "CE")["price"]
    solved = implied_volatility(price, spot, strike, T, r, "CE")
    assert solved == 0.001


def test_iv_none_when_below_intrinsic():
    # A market price below intrinsic value is a stale/bad quote, not a
    # solvable IV -- must return None, never a wrong number.
    assert implied_volatility(0.5, spot=100.0, strike=80.0, time_to_expiry_years=0.05, risk_free_rate=0.06, option_type="CE") is None


def test_iv_none_when_unreachable_even_at_max_vol():
    assert implied_volatility(1e9, spot=100.0, strike=100.0, time_to_expiry_years=0.05, risk_free_rate=0.06, option_type="CE") is None


def test_iv_none_on_missing_inputs():
    assert implied_volatility(None, 100.0, 100.0, 0.05, 0.06, "CE") is None
    assert implied_volatility(5.0, 0, 100.0, 0.05, 0.06, "CE") is None
    assert implied_volatility(5.0, 100.0, 100.0, 0, 0.06, "CE") is None
