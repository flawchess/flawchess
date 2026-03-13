---
created: 2026-03-13T10:42:44.012Z
title: Optimize for automated browser testing with Chrome Plugin
area: testing
files: []
---

## Problem

The Chessalytics frontend currently lacks automated browser-level testing. The Claude Code Chrome Plugin (claude-in-chrome MCP tools) enables browser automation — clicking elements, reading page content, filling forms, taking screenshots, and recording GIFs. To leverage this effectively, the frontend needs to be optimized for automated interaction: consistent `data-testid` attributes on interactive elements, stable selectors, and predictable page structure that browser automation can reliably target.

## Solution

- Add `data-testid` attributes to key interactive elements across the frontend (buttons, inputs, navigation links, board controls, import forms, filter controls)
- Ensure page structure is stable and predictable for automated selectors
- Consider adding accessible labels/roles where missing to improve both automation reliability and accessibility
- Document a testing strategy for using Chrome Plugin browser automation for UAT and regression testing
