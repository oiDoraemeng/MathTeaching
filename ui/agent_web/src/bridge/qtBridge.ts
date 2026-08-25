import type { AppAction } from "../state/reducer";
import type { BridgeEnvelope, ClientIntent, TimelineEvent } from "../types";

interface SignalLike { connect: (callback: (value: string) => void) => void; disconnect?: (callback: (value: string) => void) => void; }
interface QtBridgeObject { send_json: (value: string) => void; event_json?: SignalLike; }
interface QWebChannelLike { objects: Record<string, QtBridgeObject>; }
interface QtWindow extends Window { qt?: { webChannelTransport?: unknown }; QWebChannel?: new (transport: unknown, callback: (channel: QWebChannelLike) => void) => void; }

export interface QtBridgeClient { send: (intent: ClientIntent) => void; requestSnapshot: (sessionId?: string) => void; attach: (dispatch: (action: AppAction) => void) => void; detach: () => void; }

function parseEvent(raw: string): TimelineEvent | null {
  try {
    const value = JSON.parse(raw) as Record<string, unknown>;
    if (value.type === "session_snapshot") {
      return { type: "session_snapshot", session_id: String(value.session_id ?? ""), sequence: typeof value.sequence === "number" ? value.sequence : undefined, payload: (value.payload as Record<string, unknown>) ?? {} };
    }
    if (typeof value.type !== "string" || typeof value.session_id !== "string" || typeof value.payload !== "object" || !value.payload) return null;
    return value as unknown as TimelineEvent;
  } catch { return null; }
}

export function createQtBridge(): QtBridgeClient {
  const qtWindow = window as QtWindow;
  let object: QtBridgeObject | undefined;
  let listener: ((value: string) => void) | undefined;
  const pending: ClientIntent[] = [];
  const lastSequences: Record<string, number> = {};
  const send = (intent: ClientIntent) => { if (object) object.send_json(JSON.stringify(intent)); else pending.push(intent); };
  const requestSnapshot = (sessionId = "") => send({ protocol_version: 1, type: "request_snapshot", request_id: crypto.randomUUID(), session_id: sessionId, payload: {} });
  const attach = (dispatch: (action: AppAction) => void) => {
    listener = (raw) => {
      const event = parseEvent(raw);
      if (!event) return;
      if (event.type === "session_snapshot") dispatch({ type: "snapshot_loaded", snapshot: event.payload as never });
      else {
        dispatch({ type: "event_received", event });
        if (event.sequence !== undefined) {
          const key = `${event.session_id}:${event.turn_id ?? "session"}`;
          const previous = lastSequences[key] ?? 0;
          if (event.sequence > previous + 1) requestSnapshot(event.session_id);
          lastSequences[key] = Math.max(previous, event.sequence);
        }
      }
    };
    const ready = (resolved: QtBridgeObject) => { object = resolved; if (object.event_json && listener) object.event_json.connect(listener); pending.splice(0).forEach((intent) => object?.send_json(JSON.stringify(intent))); };
    const channel = qtWindow.QWebChannel;
    if (channel && qtWindow.qt?.webChannelTransport) new channel(qtWindow.qt.webChannelTransport, (value) => ready(value.objects.qtBridge));
    else {
      const fallback = (window as Window & { qtBridge?: QtBridgeObject }).qtBridge;
      if (fallback) ready(fallback);
    }
  };
  const detach = () => { if (object?.event_json && listener && object.event_json.disconnect) object.event_json.disconnect(listener); object = undefined; listener = undefined; };
  return { send, requestSnapshot, attach, detach };
}

export { parseEvent };
