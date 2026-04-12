import { useRef } from 'react';
import type { Game } from '../../game/Game';

interface Props {
  game: Game | null;
}

/** Radius of the joystick gate (outer circle) in CSS pixels. */
const JOYSTICK_RADIUS = 56;

/**
 * On-screen touch controls: a virtual analog joystick (bottom-left) and a
 * jump button (bottom-right).  Visible only on coarse-pointer (touch) devices
 * via a CSS media query so desktop players are unaffected.
 */
export function TouchControls({ game }: Props) {
  const knobRef = useRef<HTMLDivElement>(null);
  const joystickActiveId = useRef<number | null>(null);

  // ── Joystick ──────────────────────────────────────────────────────────────

  function moveKnob(dx: number, dy: number) {
    if (!knobRef.current) return;
    knobRef.current.style.transform =
      `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
  }

  function resetKnob() {
    if (!knobRef.current) return;
    knobRef.current.style.transform = 'translate(-50%, -50%)';
  }

  function handleJoystickDown(e: React.PointerEvent<HTMLDivElement>) {
    if (joystickActiveId.current !== null) return;
    joystickActiveId.current = e.pointerId;
    e.currentTarget.setPointerCapture(e.pointerId);
    updateJoystickFromPoint(e.clientX, e.clientY, e.currentTarget);
  }

  function handleJoystickMove(e: React.PointerEvent<HTMLDivElement>) {
    if (e.pointerId !== joystickActiveId.current) return;
    updateJoystickFromPoint(e.clientX, e.clientY, e.currentTarget);
  }

  function handleJoystickUp(e: React.PointerEvent<HTMLDivElement>) {
    if (e.pointerId !== joystickActiveId.current) return;
    joystickActiveId.current = null;
    resetKnob();
    game?.setTouchAxis(0, 0);
  }

  function updateJoystickFromPoint(
    clientX: number,
    clientY: number,
    base: HTMLElement,
  ) {
    const rect = base.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let dx = clientX - cx;
    let dy = clientY - cy;
    const dist = Math.hypot(dx, dy);
    if (dist > JOYSTICK_RADIUS) {
      dx = (dx / dist) * JOYSTICK_RADIUS;
      dy = (dy / dist) * JOYSTICK_RADIUS;
    }
    moveKnob(dx, dy);
    // dx → left/right (x), dy → forward/back (z) — positive dy = backward
    game?.setTouchAxis(dx / JOYSTICK_RADIUS, dy / JOYSTICK_RADIUS);
  }

  // ── Jump button ───────────────────────────────────────────────────────────

  function handleJumpDown(e: React.PointerEvent<HTMLButtonElement>) {
    e.currentTarget.setPointerCapture(e.pointerId);
    game?.triggerTouchJump();
  }

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="touch-controls" aria-hidden="true">
      {/* Virtual analog joystick */}
      <div
        className="touch-joystick-base"
        onPointerDown={handleJoystickDown}
        onPointerMove={handleJoystickMove}
        onPointerUp={handleJoystickUp}
        onPointerCancel={handleJoystickUp}
      >
        <div ref={knobRef} className="touch-joystick-knob" />
      </div>

      {/* Jump button */}
      <button
        className="touch-jump-btn"
        onPointerDown={handleJumpDown}
      >
        ↑
      </button>
    </div>
  );
}
