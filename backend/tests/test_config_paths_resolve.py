"""Regression tests for a real bug: several modules computed
Path(__file__).resolve().parents[N] one level too shallow, landing on
backend/ instead of the repo root, so config/nifty_sensex_options.json was
silently never found in production (empty {} universe, no warning visible
in a quick log scan) -- this broke both the Kite WS option subscription
(kite_provider.py) and the new Kite REST option-chain fetch (fetcher_kite.py)
via the exact same off-by-one mistake. These tests assert the real files
these modules depend on actually resolve to something that exists, so a
regression here fails loudly instead of degrading to an empty/silent state."""
from pathlib import Path


def test_fetcher_kite_options_file_resolves():
    from backend.app.options.fetcher_kite import _OPTIONS_FILE
    assert _OPTIONS_FILE.exists(), f"{_OPTIONS_FILE} does not exist -- path resolution regressed"
    assert _OPTIONS_FILE.name == "nifty_sensex_options.json"


def test_kite_provider_options_file_resolves():
    import backend.app.providers.kite_provider as kp
    src = Path(kp.__file__).resolve()
    opt_path = src.parents[3] / "config" / "nifty_sensex_options.json"
    assert opt_path.exists(), f"{opt_path} does not exist -- kite_provider's own path resolution regressed"


def test_fetcher_v2_cache_file_parent_is_real_data_dir():
    from backend.app.options.fetcher_v2 import CACHE_FILE
    # the *sibling* data/ files (watchlists.json etc) live at the repo root,
    # right next to CACHE_FILE's parent -- confirms this resolved to the real
    # project data/ directory, not a phantom backend/data/ one.
    repo_root = Path(__file__).resolve().parents[2]
    assert CACHE_FILE.parent == repo_root / "data"


def test_elite_quant_cache_dir_is_under_backend_data():
    # Same off-by-one class of bug caught here during review: this module's
    # CACHE_DIR is a sibling of historical/store.py's HIST_DIR (both are
    # backend/app/<dir>/<file>.py, three levels above backend/), so it
    # belongs in backend/data/, not the repo-root data/ used by fetcher_v2
    # above (a different, pre-existing convention for a different module).
    from backend.app.analytics.elite_quant import CACHE_DIR
    backend_dir = Path(__file__).resolve().parents[1]
    assert CACHE_DIR == backend_dir / "data" / "elite_quant"
    assert CACHE_DIR.is_dir()
