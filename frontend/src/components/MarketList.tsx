import { useState } from 'react';
import type { StarAsset } from '../market/types';
import { percentageChange } from '../market/types';
import Icon from './Icon';

interface MarketListProps {
  assets?: StarAsset[];
  selectedAssetId?: string;
  selectedPlaceholder: number;
  onSelect: (id: string) => void;
  onSelectPlaceholder: (index: number) => void;
}

const ROW_HEIGHT = 83;
const PRICE = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function MarketList({ assets, selectedAssetId, selectedPlaceholder, onSelect, onSelectPlaceholder }: MarketListProps) {
  const [sortBy, setSortBy] = useState<'price' | 'change'>('price');
  const [query, setQuery] = useState('');
  const sorted = [...(assets ?? [])].sort((a, b) => {
    const difference = sortBy === 'price' ? b.price - a.price : percentageChange(b) - percentageChange(a);
    return difference || a.name.localeCompare(b.name);
  });
  const previousRanks = new Map([...(assets ?? [])].sort((a, b) => {
    const previousChange = (asset: StarAsset) => asset.previousClose > 0 ? (asset.previousPrice - asset.previousClose) / asset.previousClose : 0;
    return (sortBy === 'price' ? b.previousPrice - a.previousPrice : previousChange(b) - previousChange(a)) || a.name.localeCompare(b.name);
  }).map((asset, index) => [asset.id, index]));
  const ranked = sorted.map((asset, index) => ({ asset, rank: index + 1, movement: (previousRanks.get(asset.id) ?? index) - index }));
  const matches = ranked.filter(({ asset }) => `${asset.name} ${asset.symbol}`.toLowerCase().includes(query.trim().toLowerCase()));
  const placeholder = assets === undefined;

  return (
    <section className="terminal-panel market-panel" aria-labelledby="market-title" id="market">
      <header className="column-header">
        <div><p className="section-kicker">The exchange</p><h2 id="market-title">Star market<span className="heading-dot">.</span></h2></div>
        <Icon name="layers" className="header-icon" size={21} />
      </header>
      <div className="market-tools">
        <label className="search-field"><Icon name="search" size={16} /><input type="search" aria-label="Search stars" placeholder="Search stars" value={query} onChange={(event) => setQuery(event.target.value)} disabled={placeholder} /></label>
        <div className="market-sort"><span>Rank by</span><div className="segmented-control" role="group" aria-label="Market ranking"><button type="button" aria-pressed={sortBy === 'price'} onClick={() => setSortBy('price')}>Price</button><button type="button" aria-pressed={sortBy === 'change'} onClick={() => setSortBy('change')}>Change</button></div></div>
      </div>
      <div className="market-column-labels"><span>Rank / star</span><span>Price / change</span></div>
      <div className="market-list-scroll">
        <div className="market-list" style={{ height: (placeholder ? 7 : matches.length) * ROW_HEIGHT }}>
          {placeholder ? Array.from({ length: 7 }, (_, index) => (
            <button type="button" key={index} className={`market-row${selectedPlaceholder === index ? ' is-selected' : ''}`} style={{ transform: `translateY(${index * ROW_HEIGHT}px)` }} onClick={() => onSelectPlaceholder(index)} aria-pressed={selectedPlaceholder === index} aria-label={`Select star placeholder ${index + 1}`}>
              <span className="market-rank placeholder-label">{'{rank}'}</span>
              <span className="star-avatar"><Icon name="orbit" size={22} /></span>
              <span className="market-star"><strong className="placeholder-label">{'{star name}'}</strong><span className="placeholder-label">{'{symbol}'}</span></span>
              <span className="market-price"><strong className="placeholder-label">{'{star price}'}</strong><span className="placeholder-label">{'{price change}'}</span></span>
            </button>
          )) : matches.map(({ asset, rank, movement }, index) => (
            <button type="button" key={asset.id} className={`market-row${selectedAssetId === asset.id ? ' is-selected' : ''}`} style={{ transform: `translateY(${index * ROW_HEIGHT}px)` }} onClick={() => onSelect(asset.id)} aria-pressed={selectedAssetId === asset.id}>
              <span className="market-rank">{rank}<span className={movement > 0 ? 'value-up' : movement < 0 ? 'value-down' : ''} aria-label={movement > 0 ? `Up ${movement} ranks` : movement < 0 ? `Down ${-movement} ranks` : 'Rank unchanged'}>{movement !== 0 ? <Icon name={movement > 0 ? 'arrow-up' : 'arrow-down'} size={11} /> : '—'}</span></span>
              <span className="star-avatar"><Icon name="orbit" size={22} /></span>
              <span className="market-star"><strong>{asset.name}</strong><span>{asset.symbol}</span></span>
              <span className="market-price"><strong>{PRICE.format(asset.price)}</strong><span className={percentageChange(asset) > 0 ? 'value-up' : percentageChange(asset) < 0 ? 'value-down' : ''}>{percentageChange(asset) > 0 ? '+' : ''}{percentageChange(asset).toFixed(2)}%</span></span>
            </button>
          ))}
        </div>
        {!placeholder && matches.length === 0 && <div className="panel-empty"><Icon name="search" size={25} /><p>{query ? 'No matching stars' : 'No stars listed yet'}</p></div>}
      </div>
      <footer className="column-footer"><span className="small-dot" /> Highest {sortBy === 'price' ? 'price' : 'change'} first<span className="footer-end">{placeholder ? '{listed stars}' : assets.length} listed</span></footer>
    </section>
  );
}
