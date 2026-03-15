---
phase: quick-20
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/game_repository.py
  - app/routers/imports.py
  - frontend/src/pages/Dashboard.tsx
autonomous: true
requirements: [DELETE-GAMES]
must_haves:
  truths:
    - "Delete button appears left of the Import button in the games header"
    - "Clicking delete opens a confirmation modal"
    - "Confirming deletion removes all user games and refreshes the view"
    - "Cancelling the modal does nothing"
  artifacts:
    - path: "app/repositories/game_repository.py"
      provides: "delete_all_games_for_user function"
      contains: "delete_all_games_for_user"
    - path: "app/routers/imports.py"
      provides: "DELETE /imports/games endpoint"
      contains: "delete"
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Delete button + confirmation dialog"
      contains: "btn-delete-games"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "DELETE /imports/games"
      via: "apiClient.delete"
      pattern: "apiClient\\.delete.*imports/games"
---

<objective>
Add a "Delete All Games" button to the left of the Import button in the games list header, with a confirmation modal. Backend DELETE endpoint removes all games + positions for the authenticated user.

Purpose: Allow users to wipe their imported data and start fresh.
Output: Working delete button with confirmation modal, backend endpoint, and UI refresh after deletion.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/repositories/game_repository.py
@app/routers/imports.py
@frontend/src/pages/Dashboard.tsx
@frontend/src/components/results/GameCardList.tsx
@frontend/src/api/client.ts
@frontend/vite.config.ts

<interfaces>
From frontend/src/components/results/GameCardList.tsx:
```typescript
interface GameCardListProps {
  games: GameRecord[];
  matchedCount: number;
  totalGames: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
  headerAction?: ReactNode;
}
```

From frontend/src/pages/Dashboard.tsx (current inlineImportButton rendering):
```typescript
const inlineImportButton = (
  <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import">
    <Download className="h-4 w-4" />
    Import
  </Button>
);
// Passed as: headerAction={inlineImportButton}
```

From app/repositories/game_repository.py:
```python
async def count_games_for_user(session: AsyncSession, user_id: int) -> int
async def bulk_insert_games(session: AsyncSession, game_rows: list[dict]) -> list[int]
async def bulk_insert_positions(session: AsyncSession, position_rows: list[dict]) -> None
```

From app/routers/imports.py:
```python
router = APIRouter(prefix="/imports", tags=["imports"])
# Uses: current_active_user, get_async_session
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add backend DELETE endpoint and repository function</name>
  <files>app/repositories/game_repository.py, app/routers/imports.py</files>
  <action>
1. In `app/repositories/game_repository.py`, add `delete_all_games_for_user(session, user_id)`:
   - Delete from `game_positions` WHERE user_id = :user_id first (child rows)
   - Delete from `games` WHERE user_id = :user_id
   - Return the count of deleted games
   - Use `from sqlalchemy import delete` (already has `func, insert, select` imported)

2. In `app/routers/imports.py`, add `DELETE /imports/games`:
   - Depends on `current_active_user` and `get_async_session`
   - Call `game_repository.delete_all_games_for_user(session, user.id)`
   - Also delete import_jobs for the user (optional cleanup): use `from app.models.import_job import ImportJob` and delete WHERE user_id = user.id
   - Commit the session explicitly (`await session.commit()`)
   - Return `{"deleted_count": count}`
   - Add the import: `from app.repositories import game_repository`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run ruff check app/repositories/game_repository.py app/routers/imports.py</automated>
  </verify>
  <done>DELETE /imports/games endpoint exists, deletes all games + positions for authenticated user, returns deleted count</done>
</task>

<task type="auto">
  <name>Task 2: Add delete button with confirmation modal to Dashboard</name>
  <files>frontend/src/pages/Dashboard.tsx</files>
  <action>
1. In `Dashboard.tsx`, add imports:
   - `Trash2` from `lucide-react` (alongside existing `Download`, `Filter`, etc.)
   - `Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter` from `@/components/ui/dialog` (already imported for bookmark dialog -- reuse existing import, just add the state)

2. Add state for the delete confirmation modal:
   - `const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);`
   - `const [isDeleting, setIsDeleting] = useState(false);`

3. Add the delete handler:
   ```typescript
   const handleDeleteAllGames = async () => {
     setIsDeleting(true);
     try {
       await apiClient.delete('/imports/games');
       setDeleteDialogOpen(false);
       // Reset analysis state
       setAnalysisResult(null);
       setPositionFilterActive(false);
       setAnalysisOffset(0);
       setDefaultOffset(0);
       // Refetch total games count and default games
       fetchTotalGames();
       defaultGames.refetch();
     } catch {
       // Error handled by axios interceptor
     } finally {
       setIsDeleting(false);
     }
   };
   ```

4. Change `inlineImportButton` to `headerActions` -- a div with both buttons:
   ```tsx
   const headerActions = (
     <div className="flex items-center gap-2">
       <Button
         variant="outline"
         size="sm"
         onClick={() => setDeleteDialogOpen(true)}
         data-testid="btn-delete-games"
       >
         <Trash2 className="h-4 w-4" />
         Delete
       </Button>
       <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import">
         <Download className="h-4 w-4" />
         Import
       </Button>
     </div>
   );
   ```

5. Replace both `headerAction={inlineImportButton}` with `headerAction={headerActions}`.

6. Add the confirmation dialog before the closing `</>` of the return, alongside the existing ImportModal and other dialogs:
   ```tsx
   <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
     <DialogContent data-testid="delete-games-modal">
       <DialogHeader>
         <DialogTitle>Delete All Games</DialogTitle>
         <DialogDescription>
           This will permanently delete all your imported games and positions. This action cannot be undone.
         </DialogDescription>
       </DialogHeader>
       <DialogFooter>
         <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} data-testid="btn-delete-cancel">
           Cancel
         </Button>
         <Button variant="destructive" onClick={handleDeleteAllGames} disabled={isDeleting} data-testid="btn-delete-confirm">
           {isDeleting ? 'Deleting...' : 'Delete All Games'}
         </Button>
       </DialogFooter>
     </DialogContent>
   </Dialog>
   ```

7. Ensure `DialogFooter` is imported -- check if it exists in `@/components/ui/dialog`. If not, add it as a simple styled div export in dialog.tsx.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>Delete button appears left of Import button. Clicking it shows confirmation modal with "Delete All Games" title, warning text, Cancel and Delete buttons. Confirming calls DELETE /imports/games and refreshes the game list. Cancel closes the modal without action.</done>
</task>

</tasks>

<verification>
- `uv run ruff check app/repositories/game_repository.py app/routers/imports.py` passes
- `cd frontend && npm run build` succeeds
- Delete button visible left of Import button in games header
- Clicking Delete opens confirmation modal
- Cancel closes modal without side effects
- Confirm deletes games and refreshes the view
</verification>

<success_criteria>
- DELETE /imports/games endpoint deletes all games + positions for authenticated user
- Delete button with Trash2 icon appears left of Import button
- Confirmation modal prevents accidental deletion
- After deletion, game list refreshes to show empty state
- All interactive elements have data-testid attributes
</success_criteria>

<output>
After completion, create `.planning/quick/20-add-a-delete-button-left-of-the-import-b/20-SUMMARY.md`
</output>
