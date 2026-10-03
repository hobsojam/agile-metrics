import "@testing-library/jest-dom/vitest";

// Recharts' ResponsiveContainer measures its parent via ResizeObserver, which
// jsdom doesn't implement (research.md §6, testing note).
class ResizeObserverStub {
  // Intentionally empty: jsdom never fires resize events, so there's
  // nothing to observe/disconnect - this stub exists only so Recharts'
  // ResponsiveContainer doesn't throw by calling a missing global.
  observe(): void {
    /* no-op */
  }
  unobserve(): void {
    /* no-op */
  }
  disconnect(): void {
    /* no-op */
  }
}

globalThis.ResizeObserver = ResizeObserverStub;
