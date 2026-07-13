"""Phase 169 PGN <-> backend round-trip check (RESEARCH Assumption A1 / Open
Question 2, PLAY-09).

Verifies that a PGN built the way frontend/src/lib/botGamePgn.ts builds one --
lichess-convention {[%clk h:mm:ss]} comments on every ply for BOTH colors, a
closed-vocabulary [Termination "..."] header, and a valid [Result "..."]
header -- is accepted end-to-end by the frozen Phase 167 backend validator
(normalize_flawchess_game). This is the guardrail that keeps the PGN "shape"
this phase's frontend code produces in lock-step with what the backend's
STORE-02 [%clk]-presence gate + Termination/Result vocabulary check requires,
without spinning up a browser or the JS toolchain.

Pure unit test, no DB required (mirrors tests/services/test_normalization.py's
TestNormalizeFlawchessGame -- normalize_flawchess_game is a pure PGN parser).
"""

from app.services.normalization import normalize_flawchess_game

_TEST_USER_ID = 7
_TEST_GAME_UUID = "8f1e0f9c-6a1b-4e6d-9a0e-1a2b3c4d5e6f"
_TEST_BOT_ELO = 1500
_TEST_PLAYER_RATING = 1450
_TEST_TC_STR = "300+3"  # base+increment SECONDS (Pattern 7), not a "5+3" display label

# Exactly the shape botGamePgn.ts's annotateClock()/finalizeBotPgn() produce:
# per-ply {[%clk h:mm:ss]} on BOTH colors, plus [Result]/[Termination]/[TimeControl].
_PHASE_169_SHAPED_PGN = (
    '[Event "?"]\n[Site "?"]\n[Date "????.??.??"]\n[Round "?"]\n'
    '[White "?"]\n[Black "?"]\n[Result "1-0"]\n'
    '[TimeControl "300+3"]\n[Termination "checkmate"]\n\n'
    "1. e4 {[%clk 0:04:57]} e5 {[%clk 0:04:55]} "
    "2. Bc4 {[%clk 0:04:53]} Nc6 {[%clk 0:04:51]} "
    "3. Qh5 {[%clk 0:04:49]} Nf6 {[%clk 0:04:47]} "
    "4. Qxf7# {[%clk 0:04:45]} 1-0\n"
)


class TestBotPgnClkRoundtrip:
    """Resolves RESEARCH Assumption A1: h:mm:ss clocks parse via python-chess's
    node.clock() and satisfy STORE-02's both-color presence gate end-to-end
    through the real normalize_flawchess_game entry point (not just a bare
    chess.pgn.read_game() smoke check).
    """

    def test_phase_169_shaped_pgn_normalizes(self) -> None:
        normalized = normalize_flawchess_game(
            _PHASE_169_SHAPED_PGN,
            _TEST_GAME_UUID,
            _TEST_USER_ID,
            "white",
            _TEST_BOT_ELO,
            _TEST_PLAYER_RATING,
            _TEST_TC_STR,
        )
        assert normalized is not None
        assert normalized.platform == "flawchess"
        assert normalized.result == "1-0"
        assert normalized.white_rating == _TEST_PLAYER_RATING
        assert normalized.black_rating == _TEST_BOT_ELO
