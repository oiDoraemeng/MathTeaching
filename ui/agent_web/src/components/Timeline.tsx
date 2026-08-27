import { useEffect, useRef } from "react";
import { EventCard } from "./EventCard";
import { TurnActions } from "./TurnActions";
import type { IntentSender, SessionProjection } from "../types";

export function Timeline({ session, onIntent, onHover, onToggleDetails }: { session: SessionProjection; onIntent: IntentSender; onHover: (turnId: string, hovered: boolean) => void; onToggleDetails: (turnId: string) => void }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "nearest" }); }, [session.turns.length, session.turns.at(-1)?.events.length]);
  return <section className="timeline" aria-label="Conversation timeline">{session.turns.length === 0 ? <div className="timeline-empty" /> : session.turns.map((turn) => <div key={turn.id} className="turn-block" onMouseEnter={() => onHover(turn.id, true)} onMouseLeave={() => onHover(turn.id, false)}><div className="user-message" role="article" aria-label="User message"><span className="sr-only">User</span><p>{turn.userMessage}</p></div>{turn.events.map((event, index) => <EventCard key={`${event.type}-${event.sequence ?? index}`} event={event} sessionId={session.id} onIntent={onIntent} technicalDetails={turn.technicalDetails} onToggleDetails={() => onToggleDetails(turn.id)} />)}<TurnActions sessionId={session.id} turn={turn} onIntent={onIntent} /></div>)}<div ref={endRef} /></section>;
}
