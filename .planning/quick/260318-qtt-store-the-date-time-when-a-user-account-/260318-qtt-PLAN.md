---
phase: quick
plan: 260318-qtt
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/user.py
  - app/users.py
  - app/schemas/users.py
  - app/routers/users.py
  - frontend/src/types/users.ts
  - alembic/versions/YYYYMMDD_HHMMSS_add_created_at_last_login_to_users.py
autonomous: true
must_haves:
  truths:
    - "User table has created_at column auto-set on registration"
    - "User table has last_login column updated on each login"
    - "GET /users/me/profile returns created_at and last_login timestamps"
  artifacts:
    - path: "app/models/user.py"
      provides: "created_at and last_login columns on User model"
      contains: "created_at"
    - path: "alembic/versions/"
      provides: "Migration adding both columns"
  key_links:
    - from: "app/users.py"
      to: "app/models/user.py"
      via: "UserManager.on_after_login updates last_login"
      pattern: "on_after_login"
---

<objective>
Add created_at and last_login timestamp columns to the User model, with an Alembic migration,
UserManager hook to update last_login on each login, and expose both fields via the profile API.

Purpose: Track when user accounts were created and when they last logged in.
Output: Migration, updated model, updated schema, updated API response.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/models/user.py
@app/users.py
@app/schemas/users.py
@app/routers/users.py
@app/repositories/user_repository.py
@frontend/src/types/users.ts
@frontend/src/hooks/useUserProfile.ts

<interfaces>
From app/models/user.py:
```python
class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chess_com_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lichess_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship("OAuthAccount", lazy="joined")
```

From app/users.py:
```python
class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
```

From app/schemas/users.py:
```python
class UserProfileResponse(BaseModel):
    chess_com_username: str | None
    lichess_username: str | None

class UserProfileUpdate(BaseModel):
    chess_com_username: str | None = None
    lichess_username: str | None = None
```

From frontend/src/types/users.ts:
```typescript
export interface UserProfile {
  chess_com_username: string | null;
  lichess_username: string | null;
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add columns, migration, and UserManager login hook</name>
  <files>app/models/user.py, app/users.py, alembic/versions/</files>
  <action>
1. In `app/models/user.py`, add two columns to the User model:
   - `created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)`
   - `last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
   - Add imports: `from datetime import datetime` and `from sqlalchemy import DateTime, func`

2. In `app/users.py`, override `on_after_login` in UserManager to update last_login:
   ```python
   async def on_after_login(
       self,
       user: User,
       request: Request | None = None,
       response: Response | None = None,
   ) -> None:
       from sqlalchemy import update as sa_update
       from app.core.database import async_session_factory
       async with async_session_factory() as session:
           await session.execute(
               sa_update(User).where(User.id == user.id).values(last_login=func.now())
           )
           await session.commit()
   ```
   - Add imports: `from fastapi import Request, Response` (Request likely already available), `from sqlalchemy import func`
   - Note: on_after_login runs OUTSIDE the request DB session, so use async_session_factory to get a fresh session.

3. Check that `async_session_factory` is exported from `app/core/database.py`. If not, check what the session maker is called and use that.

4. Generate Alembic migration:
   ```bash
   cd /home/aimfeld/Projects/Python/chessalytics
   uv run alembic revision --autogenerate -m "add created_at and last_login to users"
   ```

5. Run the migration:
   ```bash
   uv run alembic upgrade head
   ```
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run alembic heads && uv run python -c "from app.models.user import User; assert hasattr(User, 'created_at'); assert hasattr(User, 'last_login'); print('OK')"</automated>
  </verify>
  <done>User model has created_at (server_default=now) and last_login (nullable) columns. Migration applied. UserManager.on_after_login updates last_login on each login.</done>
</task>

<task type="auto">
  <name>Task 2: Expose timestamps in profile API and frontend type</name>
  <files>app/schemas/users.py, app/routers/users.py, frontend/src/types/users.ts</files>
  <action>
1. In `app/schemas/users.py`, add to UserProfileResponse:
   - `created_at: datetime` (import `from datetime import datetime`)
   - `last_login: datetime | None`

2. In `app/routers/users.py`, update the `get_profile` endpoint to include the new fields in the returned UserProfileResponse:
   - `created_at=profile.created_at`
   - `last_login=profile.last_login`

3. In `frontend/src/types/users.ts`, add to UserProfile interface:
   - `created_at: string;` (ISO datetime string from JSON)
   - `last_login: string | null;`

4. Run backend lint and frontend build to verify no errors.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run ruff check app/models/user.py app/users.py app/schemas/users.py app/routers/users.py && cd frontend && npm run build</automated>
  </verify>
  <done>GET /users/me/profile returns created_at and last_login fields. Frontend UserProfile type includes both timestamp fields. Lint and build pass.</done>
</task>

</tasks>

<verification>
- `uv run ruff check .` passes
- `npm run build` passes in frontend
- Alembic migration applied cleanly
- User model has both new columns
</verification>

<success_criteria>
- created_at column exists on users table with server_default=now()
- last_login column exists on users table, nullable
- UserManager.on_after_login updates last_login on each login (JWT and OAuth)
- GET /users/me/profile response includes created_at and last_login
- Frontend UserProfile type includes both fields
- All lint and build checks pass
</success_criteria>

<output>
After completion, create `.planning/quick/260318-qtt-store-the-date-time-when-a-user-account-/260318-qtt-SUMMARY.md`
</output>
