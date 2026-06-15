import type { CSSProperties } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { buildWikiIndex } from '../../wiki/wikiContent';
import { SECTION_EMPTY_PAGE } from '../../wiki/wikiMetadata';
import type { WikiPage, WikiSectionId } from '../../wiki/wikiTypes';
import { useGameStore } from '../../state/gameStore';
import { AbilityIcon } from './AbilityIcon';
import { useDraggableWindow } from './useDraggableWindow';

export function WikiPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const setWikiOpen = useGameStore((s) => s.setWikiOpen);
  const index = useMemo(() => buildWikiIndex(), []);
  const [activeSection, setActiveSection] = useState<WikiSectionId>('overview');
  const [query, setQuery] = useState('');
  const [activePageId, setActivePageId] = useState('overview-current-slice');

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  const normalizedQuery = query.trim().toLowerCase();
  const visiblePages = useMemo(() => {
    const sectionPages = index.pages.filter((page) => page.sectionId === activeSection);
    if (!normalizedQuery) return sectionPages;
    return sectionPages.filter((page) => pageMatchesQuery(page, normalizedQuery));
  }, [activeSection, index.pages, normalizedQuery]);

  useEffect(() => {
    if (visiblePages.some((page) => page.id === activePageId)) return;
    setActivePageId(visiblePages[0]?.id ?? '');
  }, [activePageId, visiblePages]);

  const activePage = index.pagesById[activePageId] ?? visiblePages[0] ?? null;

  return (
    <>
      <div className="wiki-backdrop" onClick={() => setWikiOpen(false)} />
      <section
        ref={panelRef}
        className={`wiki-panel panel${dragClassName}`}
        style={dragStyle}
        role="dialog"
        aria-modal="true"
        aria-labelledby="wiki-title"
        tabIndex={-1}
      >
        <header className="wiki-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="wiki-title">Guide</h2>
            <span>Game Wiki</span>
          </div>
          <button className="wiki-close" type="button" onClick={() => setWikiOpen(false)}>
            Close
          </button>
        </header>

        <div className="wiki-search-row">
          <input
            type="search"
            value={query}
            placeholder="Search current section"
            aria-label="Search wiki"
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
        </div>

        <nav className="wiki-section-tabs" aria-label="Guide sections">
          {index.sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={activeSection === section.id ? 'active' : ''}
              onClick={() => {
                setActiveSection(section.id);
                setQuery('');
                setActivePageId(index.pages.find((page) => page.sectionId === section.id)?.id ?? '');
              }}
            >
              {section.title}
            </button>
          ))}
        </nav>

        <div className="wiki-layout">
          <aside className="wiki-page-list" aria-label="Guide pages">
            {visiblePages.length === 0 ? (
              <div className="wiki-empty">{SECTION_EMPTY_PAGE[activeSection]}</div>
            ) : (
              visiblePages.map((page) => (
                <button
                  key={page.id}
                  type="button"
                  className={page.id === activePage?.id ? 'active' : ''}
                  onClick={() => setActivePageId(page.id)}
                >
                  <span>{page.title}</span>
                  {page.status === 'planned' && <em>Planned</em>}
                </button>
              ))
            )}
          </aside>

          <article className="wiki-page">
            {activePage ? <WikiPageView page={activePage} /> : <div className="wiki-empty">No guide page selected.</div>}
          </article>
        </div>
      </section>
    </>
  );
}

function WikiPageView({ page }: { page: WikiPage }) {
  const abilitySource = page.source?.kind === 'ability' ? page.source : null;
  const abilityStyle = abilitySource
    ? ({
        '--ability-primary': abilitySource.ability.visual.vfx.colors.primary,
        '--ability-secondary': abilitySource.ability.visual.vfx.colors.secondary,
        '--ability-accent': abilitySource.ability.visual.vfx.colors.accent,
        '--ability-shadow': abilitySource.ability.visual.vfx.colors.shadow,
        '--ability-glow': abilitySource.ability.visual.vfx.colors.glow,
      } as CSSProperties)
    : undefined;

  return (
    <>
      <div className="wiki-page-head">
        {abilitySource && (
          <span className="wiki-ability-icon" style={abilityStyle}>
            <AbilityIcon ability={abilitySource.ability} />
          </span>
        )}
        <div>
          <div className={`wiki-status ${page.status}`}>{page.status}</div>
          <h3>{page.title}</h3>
          {page.subtitle && <p>{page.subtitle}</p>}
        </div>
      </div>

      {page.body.map((paragraph) => (
        <p className="wiki-body-copy" key={paragraph}>
          {paragraph}
        </p>
      ))}

      {page.details && page.details.length > 0 && (
        <dl className="wiki-details">
          {page.details.map((detail) => (
            <div key={`${detail.label}-${detail.value}`}>
              <dt>{detail.label}</dt>
              <dd>{detail.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {page.tables?.map((table) => (
        <section className="wiki-table-section" key={table.title}>
          <h4>{table.title}</h4>
          <div className="wiki-table-wrap">
            <table className="wiki-table">
              <thead>
                <tr>
                  {table.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row) => (
                  <tr key={row.id}>
                    {row.cells.map((cell, index) => (
                      <td key={`${row.id}-${table.columns[index] ?? index}`}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </>
  );
}

function pageMatchesQuery(page: WikiPage, query: string): boolean {
  const searchable = [
    page.title,
    page.subtitle,
    page.status,
    ...page.tags,
    ...page.body,
    ...(page.details?.flatMap((detail) => [detail.label, detail.value]) ?? []),
    ...(page.tables?.flatMap((table) => [
      table.title,
      ...table.columns,
      ...table.rows.flatMap((row) => row.cells),
    ]) ?? []),
  ].join(' ').toLowerCase();

  return searchable.includes(query);
}
