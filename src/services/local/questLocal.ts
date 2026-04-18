import type { QuestProgress, QuestService } from '../types';

const STORAGE_KEY = 'war-js:local-quests';

export class QuestLocal implements QuestService {
  private store: Record<string, QuestProgress[]> = {};

  constructor() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) this.store = JSON.parse(raw);
    } catch {
      /* ignore */
    }
  }

  private persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.store));
    } catch {
      /* ignore */
    }
  }

  async list(characterId: string): Promise<QuestProgress[]> {
    return (this.store[characterId] ?? []).map((q) => ({
      ...q,
      counters: { ...q.counters },
    }));
  }

  async update(characterId: string, progress: QuestProgress[]): Promise<void> {
    this.store[characterId] = progress.map((q) => ({
      ...q,
      counters: { ...q.counters },
    }));
    this.persist();
  }
}
