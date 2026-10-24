import { useState } from 'react';
import type { NewsHeadline } from '../market/types';
import Icon from './Icon';

interface NewsFeedProps {
  items?: NewsHeadline[];
  onSelectAsset: (assetId: string) => void;
}

export default function NewsFeed({ items, onSelectAsset }: NewsFeedProps) {
  const [filter, setFilter] = useState<'all' | 'events' | 'signals'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const filtered = [...(items ?? [])].filter((item) => filter === 'all' || (filter === 'signals' ? item.category === 'Signal' : item.category !== 'Signal')).sort((a, b) => b.timestamp - a.timestamp);
  const placeholder = items === undefined;

  return (
    <section className="terminal-panel news-panel" aria-labelledby="news-title" id="news">
      <header className="column-header"><div><p className="section-kicker">From across the universe</p><h2 id="news-title">The dispatch<span className="heading-dot">.</span></h2></div><Icon name="signal" className="header-icon" size={22} /></header>
      <div className="news-tabs" role="group" aria-label="News filter">
        {(['all', 'events', 'signals'] as const).map((option) => <button type="button" key={option} aria-pressed={filter === option} onClick={() => { setFilter(option); setExpandedId(null); }}>{option === 'all' ? 'All updates' : option === 'events' ? 'Events' : 'Signals'}</button>)}
      </div>
      <div className="news-stream">
        {placeholder ? Array.from({ length: 4 }, (_, index) => {
          const id = `placeholder-${index}`;
          const expanded = expandedId === id;
          return (
            <article className={`news-item${index === 0 ? ' news-featured' : ''}`} key={id}>
              <div className="news-meta"><span className="news-category"><Icon name="news" size={12} /><span className="placeholder-label">{filter === 'signals' ? '{signal type}' : '{event type}'}</span></span><span className="placeholder-label">{'{time}'}</span></div>
              <button type="button" className="news-headline-button" aria-expanded={expanded} aria-controls={`news-body-${index}`} onClick={() => setExpandedId(expanded ? null : id)}><h3 className="placeholder-label">{filter === 'signals' ? '{signal headline}' : '{news headline}'}</h3><Icon name="arrow-right" size={17} /></button>
              <p className="news-summary placeholder-label">{'{news summary}'}</p>
              <p id={`news-body-${index}`} hidden={!expanded} className="news-expanded placeholder-label">{'{news detail}'}</p>
              <span className="asset-tag placeholder-label">{'{star symbol}'}</span>
            </article>
          );
        }) : filtered.map((item, index) => {
          const expanded = expandedId === item.id;
          const time = new Date(item.timestamp);
          const validTime = Number.isFinite(time.getTime());
          return (
            <article className={`news-item${index === 0 ? ' news-featured' : ''}`} key={item.id}>
              <div className="news-meta"><span className="news-category"><Icon name={item.category === 'Signal' ? 'signal' : 'news'} size={12} />{item.category}</span>{validTime ? <time dateTime={time.toISOString()}>{time.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</time> : <span className="placeholder-label">{'{time}'}</span>}</div>
              <button type="button" className="news-headline-button" aria-expanded={expanded} aria-controls={`news-detail-${index}`} onClick={() => setExpandedId(expanded ? null : item.id)}><h3>{item.headline}</h3><Icon name="arrow-right" size={17} /></button>
              <p id={`news-detail-${index}`} hidden={!expanded} className="news-expanded">{item.body}</p>
              <button type="button" className="asset-tag" onClick={() => onSelectAsset(item.assetId)}>View star <Icon name="chevron" size={11} /></button>
            </article>
          );
        })}
        {!placeholder && filtered.length === 0 && <div className="panel-empty"><Icon name="signal" size={25} /><p>No updates yet</p></div>}
      </div>
      <footer className="column-footer"><Icon name="clock" size={12} /><span>Latest updates first</span></footer>
    </section>
  );
}
