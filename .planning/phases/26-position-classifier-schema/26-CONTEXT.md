# Phase 26: Position Classifier & Schema - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute seven metadata fields for every chess position (game phase, material signature, material imbalance, endgame class, plus three tactical indicators) and add them to the `game_positions` table via Alembic migration. Pure backend — no frontend, no import wiring (Phase 27), no analytics (Phase 28).

Deliverables: `position_classifier.py` module, Alembic migration adding 7 nullable columns, comprehensive unit tests.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all decisions to Claude with guidance: "go for established best practices and important references."

### D-01: Game Phase Classification (PMETA-01)

Use **material-weight scoring** — the standard approach in chess programming engines.

- **Piece weights** (non-pawn, non-king): N=3, B=3, R=5, Q=9
- **Phase score** = sum of non-pawn, non-king material for both sides combined
- **Starting phase score** = 62 (each side: 2N+2B+2R+Q = 6+6+10+9 = 31)
- **Thresholds:**
  - Opening: phase_score >= 50
  - Middlegame: 25 <= phase_score < 50
  - Endgame: phase_score < 25
- **Validation:** Early queen trade (both queens off) drops score from 62 to 44 — correctly stays in opening/middlegame, not endgame. This satisfies success criterion #2.

Store as string enum: `'opening'`, `'middlegame'`, `'endgame'`.

### D-02: Material Signature Format (PMETA-02)

Use **repeated piece letters** in standard chess notation style (not numeric counts).

- Format: `K[pieces][pawns]_K[pieces][pawns]`
- Piece ordering within a side: Q, R, B, N, P (descending standard value)
- Multiple pieces: repeat the letter (e.g., `KRR` not `KR2`)
- Separator: underscore `_`
- **Canonical ordering:** stronger side first by total material value; if equal, lexicographic ordering of the piece string (already decided in STATE.md)
- King is always listed but not counted in material value comparison
- Examples:
  - Symmetric: `KQR_KQR` (equal material, lexicographic — identical so order doesn't matter)
  - Asymmetric: `KRRB_KRR` (stronger side first: RRB=13 > RR=10)
  - Pawn endgame: `KPPP_KPP` (3 pawns > 2 pawns in value)
  - Complex: `KQRBNPP_KQRBNPP` (full starting complement minus a few pawns)

Store as `String(40)` — starting position signature is 33 chars (`KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP`).

### D-03: Material Imbalance (PMETA-03)

Standard centipawn calculation.

- **Piece values:** P=100, N=300, B=300, R=500, Q=900
- **Imbalance** = white_material - black_material (signed integer)
- Positive = white has more material, negative = black has more
- Includes pawns in the count (unlike phase score which excludes pawns)
- Store as integer (centipawns), not float

### D-04: Endgame Class Categories (PMETA-04)

Six **mutually exclusive** categories, only assigned when `game_phase == 'endgame'` (NULL otherwise per success criterion #2).

Classification priority (evaluated in order):
1. **pawn** — Only kings and pawns (no pieces at all)
2. **pawnless** — No pawns for either side (any piece combination)
3. **rook** — Rook(s) + possibly pawns, no queens/bishops/knights
4. **minor_piece** — Bishop(s)/knight(s) + possibly pawns, no rooks/queens
5. **queen** — Queen(s) + possibly pawns, no rooks/bishops/knights
6. **mixed** — Multiple piece types present with pawns (catch-all)

Store as string enum: `'pawn'`, `'rook'`, `'minor_piece'`, `'queen'`, `'mixed'`, `'pawnless'`, or `NULL`.

### D-05: Tactical Indicators

Three boolean columns computed per position to avoid a costly second backfill pass later (TACT-01 scope, pulled forward for efficiency). Trivial to compute from `chess.Board` — near-zero marginal cost during the Phase 27 backfill that already replays every position.

- **`has_bishop_pair_white`**: `Boolean` — white has 2+ bishops
- **`has_bishop_pair_black`**: `Boolean` — black has 2+ bishops
- **`has_opposite_color_bishops`**: `Boolean` — each side has exactly one bishop and they're on different square colors

**Rationale:** The Phase 27 backfill iterates every position through `chess.Board`. Adding these indicators now costs nothing extra. A separate backfill later would repeat the entire expensive PGN replay + DB write cycle on the 3.7GB production server.

### D-06: Database Column Types

Seven new nullable columns on `game_positions`:
- `game_phase`: `String(12)` — 'opening', 'middlegame', 'endgame'
- `material_signature`: `String(40)` — canonical signature string (starting position = 33 chars, String(20) would overflow)
- `material_imbalance`: `Integer` — signed centipawns
- `endgame_class`: `String(12)` — category or NULL for non-endgame positions
- `has_bishop_pair_white`: `Boolean` — NULL until backfilled
- `has_bishop_pair_black`: `Boolean` — NULL until backfilled
- `has_opposite_color_bishops`: `Boolean` — NULL until backfilled

All nullable to support Phase 27's backfill pattern (existing rows start NULL, backfill populates them).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `app/models/game_position.py` — Current GamePosition model (target for new columns)
- `app/services/zobrist.py` — `hashes_for_game()` function showing the per-position iteration pattern that the classifier should mirror
- `app/repositories/game_repository.py` — `bulk_insert_positions()` with chunk_size that needs updating for wider rows
- `app/services/import_service.py` — Import pipeline context (Phase 27 will wire classifier here)

### Project Constraints
- `.planning/REQUIREMENTS.md` — PMETA-01 through PMETA-04 acceptance criteria
- `.planning/STATE.md` — Critical constraints: canonical signature ordering, chunk_size update needed

### Chess Programming References
- python-chess library docs — `chess.Board` API for piece scanning (`board.pieces()`, `board.occupied_co[]`)
- Standard piece values (Kaufman): P=100, N=300, B=300, R=500, Q=900

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `zobrist.py` — `compute_hashes(board)` iterates over board pieces using `chess.scan_forward(board.occupied_co[color])` and `board.piece_at(square)`. The classifier can use the same `chess.Board` API.
- `hashes_for_game()` — Shows the ply-by-ply iteration pattern over a parsed PGN. The classifier function should accept a `chess.Board` and return all four computed values.

### Established Patterns
- Model definition: SQLAlchemy 2.x `Mapped[]` with `mapped_column()` (see `game_position.py`)
- Migrations: Alembic autogenerate from model changes
- Testing: pytest with async fixtures against dev PostgreSQL

### Integration Points
- `GamePosition` model in `app/models/game_position.py` — add 7 new columns
- `bulk_insert_positions()` in `app/repositories/game_repository.py` — chunk_size must decrease from 4000 to ~2184 (15 columns instead of 8: 32767/15 = 2184)
- `hashes_for_game()` return type will need extending in Phase 27 to include classifier output — but Phase 26 only creates the standalone classifier module

</code_context>

<specifics>
## Specific Ideas

- User requested adding tactical indicator columns (bishop pair, opposite-color bishops) now to avoid a second full backfill pass later. Rationale: Phase 27 backfill already replays every position — marginal compute cost is near-zero, but a second backfill would be expensive on the constrained production server.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Bitboard storage for partial-position queries** — Different capability (partial-position matching), not classification. Remains in backlog.
- **Track user account creation/last login timestamps** — Auth concern, unrelated to position metadata. Remains in backlog.

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-position-classifier-schema*
*Context gathered: 2026-03-23*
