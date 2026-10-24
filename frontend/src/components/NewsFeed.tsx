import { useEffect, useId, useState } from 'react';
import type { MarketConnectionStatus, NewsHeadline, StarAsset } from '../market/types';
import Icon from './Icon';
import './NewsFeed.css';

interface NewsFeedProps {
  items?: NewsHeadline[];
  assets?: StarAsset[];
  status?: MarketConnectionStatus;
  error?: string | null;
  onRetry?: () => void;
  onSelectAsset: (assetId: string) => void;
}

const kindLabels: Record<NewsHeadline['kind'], string> = {
  lifecycle: 'Lifecycle',
  event: 'Event',
  rumour: 'Rumour',
  system: 'System',
};

export default function NewsFeed({
  items,
  assets = [],
  status = 'connecting',
  error,
  onRetry,
  onSelectAsset,
}: NewsFeedProps) {
  const [filter, setFilter] = useState<'all' | 'events' | 'rumours'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const bodyIdPrefix = useId();
  const assetById = new Map(assets.map((asset) => [asset.id, asset]));
  // The feed reducer preserves newest-tick order, including ties within a tick.
  const filtered = (items ?? []).filter((item) => (
    filter === 'all'
    || (filter === 'events' && (item.kind === 'lifecycle' || item.kind === 'event'))
    || (filter === 'rumours' && item.kind === 'rumour')
  ));

  useEffect(() => {
    if (expandedId !== null && items !== undefined && !items.some((item) => item.id === expandedId)) {
      setExpandedId(null);
    }
  }, [expandedId, items]);

  const hasNews = (items?.length ?? 0) > 0;
  const statusCaption = status === 'live'
    ? 'Latest ticks first'
    : status === 'connecting'
      ? 'Connecting to news'
      : `${status === 'reconnecting' ? 'Reconnecting' : 'News offline'}${hasNews ? ' · Showing received news' : ''}`;

  return (
    <section className="terminal-panel news-panel" aria-labelledby="news-title" id="news">
      <header className="column-header">
        <div>
          <p className="section-kicker">From across the universe</p>
          <h2 id="news-title">The dispatch<span className="heading-dot">.</span></h2>
        </div>
        <Icon name="signal" className="header-icon" size={22} />
      </header>
      <div className="news-tabs" role="group" aria-label="News filter">
        {(['all', 'events', 'rumours'] as const).map((option) => (
          <button type="button" key={option} aria-pressed={filter === option} onClick={() => setFilter(option)}>
            {option === 'all' ? 'All updates' : option === 'events' ? 'Events' : 'Rumours'}
          </button>
        ))}
      </div>
      {error && (
        <div className="news-feed-error" role="status">
          <p>{error}</p>
          {onRetry && <button type="button" onClick={onRetry}>Retry news</button>}
        </div>
      )}
      <div className="news-stream" role="region" aria-label="News updates" tabIndex={filtered.length > 0 ? 0 : undefined}>
        {items === undefined ? (
          <div className="panel-empty news-empty">
            <Icon name="signal" size={25} />
            <p>{error || status === 'offline' ? 'News feed unavailable' : 'Waiting for the news feed…'}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="panel-empty news-empty">
            <Icon name="news" size={25} />
            <p>{items.length === 0 ? 'No news yet' : filter === 'events' ? 'No events yet' : 'No rumours yet'}</p>
          </div>
        ) : filtered.map((item, index) => {
          const expanded = expandedId === item.id;
          const hasBody = item.body.trim().length > 0;
          const bodyId = `${bodyIdPrefix}-news-${encodeURIComponent(item.id)}`;

          return (
            <article className={`news-item${index === 0 ? ' news-featured' : ''}`} key={item.id} data-kind={item.kind}>
              <div className="news-meta">
                <span className="news-category">
                  <Icon name={item.kind === 'rumour' ? 'signal' : 'news'} size={12} />
                  {kindLabels[item.kind]}
                </span>
                <span>Tick {item.tick.toLocaleString('en-GB')}</span>
              </div>
              {hasBody ? (
                <button
                  type="button"
                  className="news-headline-button"
                  aria-expanded={expanded}
                  aria-controls={bodyId}
                  onClick={() => setExpandedId(expanded ? null : item.id)}
                >
                  <h3>{item.headline}</h3>
                  <Icon name="arrow-right" size={17} />
                </button>
              ) : <h3 className="news-static-headline">{item.headline}</h3>}
              {hasBody && <p id={bodyId} hidden={!expanded} className="news-expanded">{item.body}</p>}
              {item.assetIds.length > 0 && (
                <div className="news-asset-tags" aria-label="Related stars">
                  {[...new Set(item.assetIds)].map((assetId) => {
                    const asset = assetById.get(assetId);
                    return asset ? (
                      <button type="button" className="asset-tag" key={assetId} onClick={() => onSelectAsset(assetId)}>
                        View {asset.name} <Icon name="chevron" size={11} />
                      </button>
                    ) : <span className="asset-tag news-unavailable-asset" key={assetId} title="This star is unavailable">{assetId}</span>;
                  })}
                </div>
              )}
            </article>
          );
        })}
      </div>
      <footer className="column-footer">
        <Icon name="clock" size={12} />
        <span role="status">{statusCaption}</span>
      </footer>
    </section>
  );
}
