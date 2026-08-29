import { beforeEach, describe, expect, it } from "vitest";
import { appReducer, initialState } from "./reducer";

describe("theme_state events", () => {
  beforeEach(() => { delete document.documentElement.dataset.theme; });

  it("applies valid modes without resetting session state", () => {
    const state = initialState();
    const next = appReducer(state, { type: "event_received", event: { type: "theme_state", session_id: "", payload: { mode: "dark" } } });
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(next.theme).toBe("dark");
    expect(next.sessions).toBe(state.sessions);
    const light = appReducer(next, { type: "event_received", event: { type: "theme_state", session_id: "", payload: { mode: "light" } } });
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(light.theme).toBe("light");
  });

  it("ignores malformed modes", () => {
    const state = initialState();
    const next = appReducer(state, { type: "event_received", event: { type: "theme_state", session_id: "", payload: { mode: "blue" } } });
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(next).toBe(state);
  });
});
