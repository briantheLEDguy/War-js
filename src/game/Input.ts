import { useGameStore } from '../state/gameStore';

export class Input {
  private keys = new Set<string>();
  private target: HTMLElement;
  private pressedThisFrame = new Set<string>();

  mouseLeftDown = false;
  mouseRightDown = false;
  mouseLeftClickedThisFrame = false;
  mouseRightClickedThisFrame = false;
  lastClickNDC = new Float32Array(2); // [-1,1] screen space
  lastRightClickNDC = new Float32Array(2); // [-1,1] screen space

  private leftMouseStartX = 0;
  private leftMouseStartY = 0;
  private leftMouseClickBlocked = false;
  private rightMouseStartX = 0;
  private rightMouseStartY = 0;
  private rightMouseClickBlocked = false;
  private readonly clickSlopPx = 6;

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
    const k = e.code;
    const target = e.target as HTMLElement | null;

    if (k === 'Escape') {
      this.clearHeldState();
      if (e.repeat || isChatTextEntry(target) || useGameStore.getState().chatFocused) return;
      e.preventDefault();
      const store = useGameStore.getState();
      if (!store.closeTopWindow()) store.setSettingsOpen(true);
      return;
    }

    if (this.shouldIgnoreKey(e)) {
      this.clearHeldState();
      return;
    }
    const gmBuildMode = useGameStore.getState().gmBuildMode;
    if (gmBuildMode && (k === 'Delete' || k === 'Backspace')) {
      if (isFormControl(target)) {
        this.clearHeldState();
        return;
      }
      e.preventDefault();
    }
    if (gmBuildMode && (k === 'Tab' || (isMovementKey(k) && isFormControl(target)))) {
      e.preventDefault();
    }
    if (!this.keys.has(k)) this.pressedThisFrame.add(k);
    this.keys.add(k);
  };
  private onKeyUp = (e: KeyboardEvent) => {
    this.keys.delete(e.code);
  };
  private onMouseDown = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    if (e.button === 0) {
      e.preventDefault();
      this.mouseLeftDown = true;
      this.leftMouseStartX = e.clientX;
      this.leftMouseStartY = e.clientY;
      this.leftMouseClickBlocked = this.mouseRightDown;
      if (this.mouseRightDown) this.rightMouseClickBlocked = true;
    }
    if (e.button === 2) {
      e.preventDefault();
      this.mouseRightDown = true;
      this.rightMouseStartX = e.clientX;
      this.rightMouseStartY = e.clientY;
      this.rightMouseClickBlocked = this.mouseLeftDown;
      if (this.mouseLeftDown) this.leftMouseClickBlocked = true;
    }
  };
  private onMouseMove = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    if (this.mouseLeftDown && !this.leftMouseClickBlocked) {
      const dx = e.clientX - this.leftMouseStartX;
      const dy = e.clientY - this.leftMouseStartY;
      if (Math.hypot(dx, dy) > this.clickSlopPx) this.leftMouseClickBlocked = true;
    }
    if (this.mouseRightDown && !this.rightMouseClickBlocked) {
      const dx = e.clientX - this.rightMouseStartX;
      const dy = e.clientY - this.rightMouseStartY;
      if (Math.hypot(dx, dy) > this.clickSlopPx) this.rightMouseClickBlocked = true;
    }
  };
  private onMouseUp = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    if (e.button === 0) {
      if (!this.leftMouseClickBlocked) {
        this.setClickNDC(e.clientX, e.clientY, this.lastClickNDC);
        this.mouseLeftClickedThisFrame = true;
      }
      this.mouseLeftDown = false;
      this.leftMouseClickBlocked = false;
    }
    if (e.button === 2) {
      if (!this.rightMouseClickBlocked) {
        this.setClickNDC(e.clientX, e.clientY, this.lastRightClickNDC);
        this.mouseRightClickedThisFrame = true;
      }
      this.mouseRightDown = false;
      this.rightMouseClickBlocked = false;
    }
  };
  private onContextMenu = (e: MouseEvent) => e.preventDefault();
  private onWindowBlur = () => this.clearHeldState();
  private onVisibilityChange = () => {
    if (document.visibilityState !== 'visible') this.clearHeldState();
  };
  private onFocusIn = (e: FocusEvent) => {
    if (isFormControl(e.target as HTMLElement | null)) this.clearHeldState();
  };

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
    window.addEventListener('blur', this.onWindowBlur);
    document.addEventListener('visibilitychange', this.onVisibilityChange);
    document.addEventListener('focusin', this.onFocusIn);
    target.addEventListener('pointerdown', this.onMouseDown);
    window.addEventListener('pointermove', this.onMouseMove);
    window.addEventListener('pointerup', this.onMouseUp);
    target.addEventListener('contextmenu', this.onContextMenu);
    target.addEventListener('touchstart', this.onTouchStart, { passive: true });
    target.addEventListener('touchend', this.onTouchEnd, { passive: true });
    target.addEventListener('touchcancel', this.onTouchCancel, { passive: true });
  }

  private shouldIgnoreKey(e: KeyboardEvent): boolean {
    const t = e.target as HTMLElement | null;
    return isTextEntryControl(t);
  }

  private setClickNDC(clientX: number, clientY: number, target: Float32Array) {
    const rect = this.target.getBoundingClientRect();
    target[0] = ((clientX - rect.left) / rect.width) * 2 - 1;
    target[1] = -(((clientY - rect.top) / rect.height) * 2 - 1);
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
    this.mouseRightClickedThisFrame = false;
    this.touchJumpThisFrame = false;
  }

  clearHeldState() {
    this.keys.clear();
    this.pressedThisFrame.clear();
    this.mouseLeftDown = false;
    this.mouseRightDown = false;
    this.mouseLeftClickedThisFrame = false;
    this.mouseRightClickedThisFrame = false;
    this.leftMouseClickBlocked = false;
    this.rightMouseClickBlocked = false;
    this.touchMoveX = 0;
    this.touchMoveZ = 0;
    this.touchJumpThisFrame = false;
    this.tapTouchId = null;
  }

  dispose() {
    window.removeEventListener('keydown', this.onKeyDown);
    window.removeEventListener('keyup', this.onKeyUp);
    window.removeEventListener('blur', this.onWindowBlur);
    document.removeEventListener('visibilitychange', this.onVisibilityChange);
    document.removeEventListener('focusin', this.onFocusIn);
    this.target.removeEventListener('pointerdown', this.onMouseDown);
    window.removeEventListener('pointermove', this.onMouseMove);
    window.removeEventListener('pointerup', this.onMouseUp);
    this.target.removeEventListener('contextmenu', this.onContextMenu);
    this.target.removeEventListener('touchstart', this.onTouchStart);
    this.target.removeEventListener('touchend', this.onTouchEnd);
    this.target.removeEventListener('touchcancel', this.onTouchCancel);
  }
}

function isFormControl(target: HTMLElement | null): boolean {
  if (!target) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'BUTTON' || target.isContentEditable;
}

function isTextEntryControl(target: HTMLElement | null): boolean {
  if (!target) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  if (tag === 'TEXTAREA') return true;
  if (tag !== 'INPUT') return false;
  const input = target as HTMLInputElement;
  return !['button', 'checkbox', 'color', 'file', 'number', 'radio', 'range', 'reset', 'submit'].includes(input.type);
}

function isChatTextEntry(target: HTMLElement | null): boolean {
  if (!target || !isTextEntryControl(target)) return false;
  return Boolean(target.closest('.chat'));
}

function isMovementKey(code: string): boolean {
  return code === 'KeyW' || code === 'KeyA' || code === 'KeyS' || code === 'KeyD' || code === 'Space';
}
