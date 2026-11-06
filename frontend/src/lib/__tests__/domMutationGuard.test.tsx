// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import * as Sentry from '@sentry/react';
import { installDomMutationGuard } from '@/lib/domMutationGuard';

vi.mock('@sentry/react', () => ({ addBreadcrumb: vi.fn() }));

const TRANSLATED_TEXT = 'перевод';

/** What Google Translate does: swap the text node React holds for a <font>. */
function translateTextNode(container: HTMLElement, text: string): void {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.nodeValue !== text) continue;
    const font = document.createElement('font');
    font.textContent = TRANSLATED_TEXT;
    node.parentNode!.replaceChild(font, node);
    return;
  }
  throw new Error('text node not found');
}

/** Commits parent.insertBefore(<b>, textNode) when `badge` turns on. */
function InsertScenario({ badge }: { badge: boolean }) {
  return (
    <p>
      {badge ? <b>new</b> : null}
      Hello
    </p>
  );
}

/** Commits parent.removeChild(textNode) when `text` turns off. */
function RemoveScenario({ text }: { text: boolean }) {
  return (
    <p>
      <i>keep</i>
      {text ? 'Hello' : null}
    </p>
  );
}

const originalInsertBefore = Node.prototype.insertBefore;
const originalRemoveChild = Node.prototype.removeChild;

afterEach(() => {
  cleanup();
  Node.prototype.insertBefore = originalInsertBefore;
  Node.prototype.removeChild = originalRemoveChild;
  vi.mocked(Sentry.addBreadcrumb).mockClear();
});

describe('without the guard (control: proves the repro is real)', () => {
  it('insertBefore against a translated text node crashes React', () => {
    const { container, rerender } = render(<InsertScenario badge={false} />);
    translateTextNode(container, 'Hello');
    expect(() => rerender(<InsertScenario badge />)).toThrow();
  });

  it('removeChild of a translated text node crashes React', () => {
    const { container, rerender } = render(<RemoveScenario text />);
    translateTextNode(container, 'Hello');
    expect(() => rerender(<RemoveScenario text={false} />)).toThrow();
  });
});

describe('with the guard', () => {
  beforeEach(() => {
    installDomMutationGuard();
  });

  it('React survives inserting next to a translated text node and shows the new node', () => {
    const { container, rerender } = render(<InsertScenario badge={false} />);
    translateTextNode(container, 'Hello');
    expect(() => rerender(<InsertScenario badge />)).not.toThrow();
    expect(container.querySelector('b')?.textContent).toBe('new');
    expect(container.textContent).toContain(TRANSLATED_TEXT);
  });

  it('React survives removing a translated text node and keeps its siblings', () => {
    const { container, rerender } = render(<RemoveScenario text />);
    translateTextNode(container, 'Hello');
    expect(() => rerender(<RemoveScenario text={false} />)).not.toThrow();
    expect(container.querySelector('i')?.textContent).toBe('keep');
  });

  it('inserts before the wrapper when the reference node was wrapped', () => {
    const parent = document.createElement('div');
    const reference = document.createTextNode('ref');
    const wrapper = document.createElement('font');
    wrapper.appendChild(reference);
    const last = document.createElement('span');
    parent.append(wrapper, last);
    const inserted = document.createElement('b');

    expect(parent.insertBefore(inserted, reference)).toBe(inserted);

    expect(Array.from(parent.childNodes)).toEqual([inserted, wrapper, last]);
    expect(Sentry.addBreadcrumb).toHaveBeenCalledOnce();
  });

  it('appends when the reference node is gone from the parent', () => {
    const parent = document.createElement('div');
    const first = document.createElement('span');
    parent.appendChild(first);
    const inserted = document.createElement('b');

    parent.insertBefore(inserted, document.createTextNode('detached'));

    expect(Array.from(parent.childNodes)).toEqual([first, inserted]);
  });

  it('removes a wrapped child from its real parent', () => {
    const parent = document.createElement('div');
    const wrapper = document.createElement('font');
    const child = document.createElement('span');
    wrapper.appendChild(child);
    parent.appendChild(wrapper);

    expect(parent.removeChild(child)).toBe(child);

    expect(child.parentNode).toBeNull();
    expect(parent.firstChild).toBe(wrapper);
  });

  it('leaves a child alone when it lives outside the parent', () => {
    const parent = document.createElement('div');
    const elsewhere = document.createElement('div');
    const child = document.createElement('span');
    elsewhere.appendChild(child);

    expect(parent.removeChild(child)).toBe(child);

    expect(child.parentNode).toBe(elsewhere);
  });

  it('leaves normal DOM calls untouched and records no breadcrumb', () => {
    const parent = document.createElement('div');
    const second = document.createElement('span');
    parent.appendChild(second);
    const first = document.createElement('b');
    const third = document.createElement('i');

    parent.insertBefore(first, second);
    parent.insertBefore(third, null);
    expect(Array.from(parent.childNodes)).toEqual([first, second, third]);

    expect(parent.removeChild(second)).toBe(second);
    expect(Array.from(parent.childNodes)).toEqual([first, third]);
    expect(Sentry.addBreadcrumb).not.toHaveBeenCalled();
  });
});
