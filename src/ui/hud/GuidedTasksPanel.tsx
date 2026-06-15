import { useState } from 'react';
import { useGameStore } from '../../state/gameStore';
import { GUIDED_TASKS, guidedTaskCompletion } from './guidedTasks';
import { useDraggableWindow } from './useDraggableWindow';

export function GuidedTasksPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const guidedTasks = useGameStore((s) => s.guidedTasks);
  const resetGuidedTasks = useGameStore((s) => s.resetGuidedTasks);
  const [collapsed, setCollapsed] = useState(false);
  const progress = guidedTaskCompletion(guidedTasks);
  const nextTask = GUIDED_TASKS.find((task) => !guidedTasks[task.id]) ?? null;

  if (progress.completed === progress.total) {
    return (
      <button
        type="button"
        className="guided-tasks-toggle"
        onClick={() => {
          resetGuidedTasks();
          setCollapsed(false);
        }}
        aria-label="Reset first-session goals"
      >
        Tasks {progress.completed}/{progress.total}
      </button>
    );
  }

  if (collapsed) {
    return (
      <button
        type="button"
        className="guided-tasks-toggle"
        onClick={() => setCollapsed(false)}
        aria-label="Show first-session goals"
      >
        Tasks {progress.completed}/{progress.total}
      </button>
    );
  }

  return (
    <section
      ref={panelRef}
      className={`guided-tasks-panel panel${dragClassName}`}
      style={dragStyle}
      aria-labelledby="guided-tasks-title"
    >
      <header className="guided-tasks-header draggable-window-handle" {...dragHandleProps}>
        <div>
          <h2 id="guided-tasks-title">First Steps</h2>
          <span>{progress.completed}/{progress.total} complete</span>
        </div>
        <button type="button" onClick={() => setCollapsed(true)}>Min</button>
      </header>

      <div className="guided-progress-track" aria-hidden="true">
        <div style={{ width: `${progress.percent}%` }} />
      </div>

      {nextTask && (
        <div className="guided-next">
          <strong>{nextTask.label}</strong>
          <span>{nextTask.detail}</span>
        </div>
      )}

      <ul className="guided-task-list" aria-label="First-session goals">
        {GUIDED_TASKS.map((task) => (
          <li className={guidedTasks[task.id] ? 'complete' : ''} key={task.id}>
            <span className="guided-check" aria-hidden="true">
              {guidedTasks[task.id] ? 'OK' : '-'}
            </span>
            <span>{task.label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
