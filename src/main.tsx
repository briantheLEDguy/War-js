import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './ui/App';

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: '#0a0a0a', color: '#e6dcc0', fontFamily: 'monospace', padding: 32,
        }}>
          <h2 style={{ color: '#c9a257', marginTop: 0 }}>War-js — startup error</h2>
          <pre style={{ color: '#c0392b', whiteSpace: 'pre-wrap', maxWidth: 600 }}>
            {error.message}
          </pre>
          <p style={{ color: '#8a8170', fontSize: 13 }}>
            Open the browser console for the full stack trace, then reload.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

const el = document.getElementById('root');
if (!el) throw new Error('Missing #root element — check index.html');
createRoot(el).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
