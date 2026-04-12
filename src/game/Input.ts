export class Input {
  private keys = new Set<string>();
  private target: HTMLElement;
  private pressedThisFrame = new Set<string>();

  mouseLeftDown = false;
  mouseRightDown = false;
  mouseLeftClickedThisFrame = false;
  lastClickNDC = new Float32Array(2); // [-1,1] screen space

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

  constructor(target: HTMLElement) {
    this.target = target;
    window.addEventListener('keydown', this.onKeyDown);
    window.addEventListener('keyup', this.onKeyUp);
    target.addEventListener('mousedown', this.onMouseDown);
    window.addEventListener('mouseup', this.onMouseUp);
    target.addEventListener('contextmenu', this.onContextMenu);
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
  endFrame() {
    this.pressedThisFrame.clear();
    this.mouseLeftClickedThisFrame = false;
  }
  dispose() {
    window.removeEventListener('keydown', this.onKeyDown);
    window.removeEventListener('keyup', this.onKeyUp);
    this.target.removeEventListener('mousedown', this.onMouseDown);
    window.removeEventListener('mouseup', this.onMouseUp);
    this.target.removeEventListener('contextmenu', this.onContextMenu);
  }
}
