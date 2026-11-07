// ── DOM mutation guard ────────────────────────────────────────────────────
// FLAWCHESS-BV: Google Translate swaps the text nodes React holds for <font>
// elements. React still has the original node, so its next commit calls
// insertBefore/removeChild against a node that is no longer a child of that
// parent. The DOM throws NotFoundError and the whole app lands on the error
// boundary. Wrapping these two methods is the workaround for
// facebook/react#11538, which has no fix in React itself.
//
// Unlike the commonly copied snippet, a mismatched insertBefore still inserts
// the node, so translated pages don't silently lose content.

import * as Sentry from '@sentry/react';

/** Leaves a trail on later events, since the guard would otherwise hide a real React bug. */
function recordMismatch(operation: 'insertBefore' | 'removeChild'): void {
  Sentry.addBreadcrumb({
    category: 'dom-mutation-guard',
    level: 'warning',
    message: `${operation} target is not a direct child`,
  });
}

/** The direct child of `parent` that holds `node`, or null if `node` isn't under `parent`. */
function directChildContaining(parent: Node, node: Node): Node | null {
  let current: Node | null = node;
  while (current && current.parentNode !== parent) {
    current = current.parentNode;
  }
  return current;
}

/** Call once, before React's first commit. Calls with a matching parent behave as before. */
export function installDomMutationGuard(): void {
  const originalInsertBefore = Node.prototype.insertBefore;
  const originalRemoveChild = Node.prototype.removeChild;

  Node.prototype.insertBefore = function <T extends Node>(
    this: Node,
    node: T,
    child: Node | null,
  ): T {
    if (!child || child.parentNode === this) {
      return originalInsertBefore.call(this, node, child) as T;
    }
    recordMismatch('insertBefore');
    return originalInsertBefore.call(this, node, directChildContaining(this, child)) as T;
  };

  Node.prototype.removeChild = function <T extends Node>(this: Node, child: T): T {
    if (child.parentNode === this) {
      return originalRemoveChild.call(this, child) as T;
    }
    recordMismatch('removeChild');
    const actualParent = child.parentNode;
    if (actualParent && this.contains(actualParent)) {
      originalRemoveChild.call(actualParent, child);
    }
    return child;
  };
}
