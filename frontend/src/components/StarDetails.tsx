import type { ReactNode } from 'react';
import type { StarAsset } from '../market/types';
import { priceChange } from '../market/types';
import CandleChart from './CandleChart';
import Icon from './Icon';

interface StarDetailsProps {
  asset?: StarAsset;
  children?: ReactNode;
}

const NUMBER = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });
const PRICE = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const LUMINOSITY = new Intl.NumberFormat('en-GB', { maximumSignificantDigits: 4 });

export default function StarDetails({ asset, children }: StarDetailsProps) {
  const change = asset ? priceChange(asset) : undefined;
  const stats = [
    { label: 'Luminosity · L☉', value: asset ? (asset.luminosity >= 1e6 ? asset.luminosity.toExponential(2) : LUMINOSITY.format(asset.luminosity)) : '{luminosity}' },
    { label: 'Mass · M☉', value: asset ? NUMBER.format(asset.mass) : '{mass}' },
    { label: 'Birth spectral type', value: asset?.spectralType ?? '{spectral type}' },
    { label: 'Birth temperature · K', value: asset ? NUMBER.format(asset.temperature) : '{temperature}' },
  ];

  return (
    <section className="terminal-panel detail-panel" aria-labelledby="detail-title" id="star-details" data-stage={asset?.stage}>
      <header className="column-header"><div><p className="section-kicker">A closer look</p><h2 id="detail-title">In focus<span className="heading-dot">.</span></h2></div><span className="detail-symbol placeholder-label">{asset?.symbol ?? '{symbol}'}</span></header>
      <div className="star-overview">
        <div className="star-identity"><span className="star-avatar star-avatar-large" style={asset ? { color: asset.color, borderColor: asset.color } : undefined}><Icon name="orbit" size={29} /></span><div><h3 className={!asset ? 'placeholder-label' : undefined}>{asset?.name ?? '{star name}'}</h3><p className={!asset ? 'placeholder-label' : 'stage-label'} style={asset ? { color: asset.color } : undefined}>{asset?.classification ?? '{star type}'}</p></div></div>
        <div className="selected-price"><span className={!asset ? 'placeholder-label' : undefined}>{asset ? PRICE.format(asset.price) : '{star price}'}</span><span className="price-unit">CR</span></div>
        <div className={`selected-change ${(change ?? 0) > 0 ? 'value-up' : (change ?? 0) < 0 ? 'value-down' : ''}`}>{change === undefined ? <span className="placeholder-label">{'{price change}'}</span> : change === null ? <span>—</span> : <>{change !== 0 && <Icon name={change < 0 ? 'arrow-down' : 'arrow-up'} size={13} />}<span>{change > 0 ? '+' : ''}{PRICE.format(change)} CR</span></>}<span className="change-caption">vs. previous tick</span></div>
      </div>
      <CandleChart candles={asset?.history} />
      {children}
      <section className="star-fundamentals" aria-labelledby="fundamentals-title"><div className="subsection-heading"><h3 id="fundamentals-title">Stellar fundamentals</h3><Icon name="orbit" size={15} /></div><dl className="fundamentals-grid">{stats.map((stat) => <div key={stat.label}><dt>{stat.label}</dt><dd className={!asset ? 'placeholder-label' : undefined}>{stat.value}</dd></div>)}</dl></section>
      <section className="star-brief" aria-labelledby="star-brief-title"><span className="brief-icon"><Icon name="signal" size={17} /></span><div><h3 id="star-brief-title">On the radar</h3><p className={!asset?.signal ? 'placeholder-label' : undefined}>{asset?.signal ?? '{star insight}'}</p></div></section>
    </section>
  );
}
