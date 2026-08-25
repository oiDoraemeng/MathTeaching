import { describe, expect, it, vi } from "vitest";
import { createQtBridge, parseEvent } from "./qtBridge";

describe("qtBridge", () => {
  it("sends only serialized intents once the channel is ready", () => {
    const send_json = vi.fn();
    Object.assign(window, { qtBridge: { send_json } });
    const bridge = createQtBridge();
    bridge.send({ protocol_version: 1, type: "request_snapshot", request_id: "r1", session_id: "s1", payload: {} });
    bridge.attach(vi.fn());
    expect(send_json).toHaveBeenCalledTimes(1);
    expect(JSON.parse(send_json.mock.calls[0][0])).toMatchObject({ type: "request_snapshot", session_id: "s1" });
    delete (window as Window & { qtBridge?: unknown }).qtBridge;
  });
  it("rejects malformed events before reducer dispatch", () => {
    expect(parseEvent("not-json")).toBeNull();
    expect(parseEvent(JSON.stringify({ type: "execution", session_id: "s1", payload: { text: "ok" } }))).toMatchObject({ type: "execution" });
    expect(parseEvent(JSON.stringify({ type: "execution", payload: {} }))).toBeNull();
  });
  it("requests a snapshot after a sequence gap", () => {
    const send_json = vi.fn();
    Object.assign(window, { qtBridge: { send_json, event_json: { connect: (listener: (raw: string) => void) => { (window as Window & { __listener?: (raw: string) => void }).__listener = listener; } } } });
    const dispatch = vi.fn();
    const bridge = createQtBridge();
    bridge.attach(dispatch);
    (window as Window & { __listener?: (raw: string) => void }).__listener?.(JSON.stringify({ type: "execution", session_id: "s1", turn_id: "t1", sequence: 3, payload: {} }));
    expect(send_json).toHaveBeenCalledWith(expect.stringContaining('"type":"request_snapshot"'));
    delete (window as Window & { qtBridge?: unknown }).qtBridge;
  });
});
