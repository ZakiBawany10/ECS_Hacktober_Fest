import type { StarAsset } from '../market/types';
import { percentageChange } from '../market/types';
import CandleChart from './CandleChart';
import Icon from './Icon';

interface StarDetailsProps {
  asset?: StarAsset;
}

const NUMBER = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });
const PRICE = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function StarDetails({ asset }: StarDetailsProps) {
  const change = asset ? percentageChange(asset) : undefined;
  const stats = [
    { label: 'Luminosity', value: asset ? NUMBER.format(asset.luminosity) : '{luminosity}' },
    { label: 'Radius', value: asset ? NUMBER.format(asset.radius) : '{radius}' },
    { label: 'Mass', value: asset ? NUMBER.format(asset.mass) : '{mass}' },
    { label: 'Classification', value: asset?.classification ?? '{classification}' },
  ];

  return (
    <section className="terminal-panel detail-panel" aria-labelledby="detail-title" id="star-details">
      <header className="column-header"><div><p className="section-kicker">A closer look</p><h2 id="detail-title">In focus<span className="heading-dot">.</span></h2></div><span className="detail-symbol placeholder-label">{asset?.symbol ?? '{symbol}'}</span></header>
      <div className="star-overview">
        <div className="star-identity"><span className="star-avatar star-avatar-large"><Icon name="orbit" size={29} /></span><div><h3 className={!asset ? 'placeholder-label' : undefined}>{asset?.name ?? '{star name}'}</h3><p className={!asset ? 'placeholder-label' : undefined}>{asset?.classification ?? '{star type}'}</p></div></div>
        <div className="selected-price"><span className={!asset ? 'placeholder-label' : undefined}>{asset ? PRICE.format(asset.price) : '{star price}'}</span><span className="price-unit">CR</span></div>
        <div className={`selected-change ${change !== undefined && change > 0 ? 'value-up' : change !== undefined && change < 0 ? 'value-down' : ''}`}>{change === undefined ? <span className="placeholder-label">{'{price change}'}</span> : <>{change !== 0 && <Icon name={change < 0 ? 'arrow-down' : 'arrow-up'} size={13} />}<span>{change > 0 ? '+' : ''}{change.toFixed(2)}%</span></>}<span className="change-caption">vs. previous close</span></div>
      </div>
      <CandleChart candles={asset?.history} />
      <section className="star-fundamentals" aria-labelledby="fundamentals-title"><div className="subsection-heading"><h3 id="fundamentals-title">Stellar fundamentals</h3><Icon name="orbit" size={15} /></div><dl className="fundamentals-grid">{stats.map((stat) => <div key={stat.label}><dt>{stat.label}</dt><dd className={!asset ? 'placeholder-label' : undefined}>{stat.value}</dd></div>)}</dl></section>
      <section className="star-brief" aria-labelledby="star-brief-title"><span className="brief-icon"><Icon name="signal" size={17} /></span><div><h3 id="star-brief-title">On the radar</h3><p className={!asset ? 'placeholder-label' : undefined}>{asset?.signal ?? '{star insight}'}</p></div></section>
    </section>
  );
}
