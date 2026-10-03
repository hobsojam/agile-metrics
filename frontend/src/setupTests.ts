import "@testing-library/jest-dom/vitest";

// Recharts' ResponsiveContainer measures its parent via ResizeObserver, which
// jsdom doesn't implement (research.md §6, testing note).
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.ResizeObserver = ResizeObserverStub;
