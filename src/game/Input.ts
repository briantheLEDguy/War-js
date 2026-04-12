export class Input {
  private keys = new Set<string>();
  private target: HTMLElement;
  private pressedThisFrame = new Set<string>();

  mouseLeftDown = false;
  mouseRightDown = false;
  mouseLeftClickedThisFrame = false;
  lastClickNDC = new Float32Array(2); // [-1,1] screen space

  // Touch-driven virtual joystick axis (-1 to 1 each)
  touchMoveX = 0;
  touchMoveZ = 0;
  // Set to true for one frame when the touch jump button is pressed
  touchJumpThisFrame = false;

  // Tap-to-target: tracks a single touch to detect short taps on the canvas
  private tapTouchId: number | null = null;
  private tapStartX = 0;
  private tapStartY = 0;

  private onKeyDown = (e: KeyboardEvent) => {
    if (this.shouldIgnoreKey(e)) return;
    const k = e.code;
    if (!this.keys.has(k)) this.pressedThisFrame.add(k);
    this.keys.add(k);
  };
  private onKeyUp = (e: KeyboardEvent) => {
    this.keys.delete(e.code);
  };
  private onMouseDown = (e: MouseEvent) => {
    if (e.button === 0) {
      this.mouseLeftDown = true;
      this.mouseLeftClickedThisFrame = true;
      const rect = this.target.getBoundingClientRect();
      this.lastClickNDC[0] = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.lastClickNDC[1] = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    }
    if (e.button === 2) this.mouseRightDown = true;
  };
  private onMouseUp = (e: MouseEvent) => {
    if (e.button === 0) this.mouseLeftDown = false;
    if (e.button === 2) this.mouseRightDown = false;
  };
  private onContextMenu = (e: MouseEvent) => e.preventDefault();

  // Touch tap-to-target (short taps on the canvas become left-clicks)
  private onTouchStart = (e: TouchEvent) => {
    if (this.tapTouchId !== null) return;
    const t = e.changedTouches[0];
    this.tapTouchId = t.identifier;
    this.tapStartX = t.clientX;
    this.tapStartY = t.clientY;
  };
  private onTouchEnd = (e: TouchEvent) => {
    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      if (t.identifier !== this.tapTouchId) continue;
      this.tapTouchId = null;
      const dx = t.clientX - this.tapStartX;
      const dy = t.clientY - this.tapStartY;
      // Treat as a tap if the finger barely moved
      if (Math.hypot(dx, dy) < 12) {
        const rect = this.target.getBoundingClientRect();
        this.mouseLeftClickedThisFrame = true;
        this.lastClickNDC[0] = ((t.clientX - rect.left) / rect.width) * 2 - 1;
        this.lastClickNDC[1] = -(((t.clientY - rect.top) / rect.height) * 2 - 1);
      }
    }
  };
  private onTouchCancel = () => { this.tapTouchId = null; };

  constructor(target: HTMLElement) {
    this.target = target;
    window.addEventListener('keydown', this.onKeyDown);
    window.addEventListener('keyup', this.onKeyUp);
    target.addEventListener('mousedown', this.onMouseDown);
    window.addEventListener('mouseup', this.onMouseUp);
    target.addEventListener('contextmenu', this.onContextMenu);
    target.addEventListener('touchstart', this.onTouchStart, { passive: true });
    target.addEventListener('touchend', this.onTouchEnd, { passive: true });
    target.addEventListener('touchcancel', this.onTouchCancel, { passive: true });
  }

  private shouldIgnoreKey(e: KeyboardEvent): boolean {
    const t = e.target as HTMLElement | null;
    if (!t) return false;
    const tag = t.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || t.isContentEditable;
  }

  isDown(code: string): boolean {
    return this.keys.has(code);
  }
  wasPressed(code: string): boolean {
    return this.pressedThisFrame.has(code);
  }

  /** Called each frame by TouchControls to update the virtual joystick axis. */
  setTouchAxis(x: number, z: number) {
    this.touchMoveX = x;
    this.touchMoveZ = z;
  }

  /** Called by the touch jump button; the flag is consumed once per frame. */
  triggerTouchJump() {
    this.touchJumpThisFrame = true;
  }

  endFrame() {
    this.pressedThisFrame.clear();
    this.mouseLeftClickedThisFrame = false;
    this.touchJumpThisFrame = false;
  }
  dispose() {
    window.removeEventListener('keydown', this.onKeyDown);
    window.removeEventListener('keyup', this.onKeyUp);
    this.target.removeEventListener('mousedown', this.onMouseDown);
    window.removeEventListener('mouseup', this.onMouseUp);
    this.target.removeEventListener('contextmenu', this.onContextMenu);
    this.target.removeEventListener('touchstart', this.onTouchStart);
    this.target.removeEventListener('touchend', this.onTouchEnd);
    this.target.removeEventListener('touchcancel', this.onTouchCancel);
  }
}
