import { useEffect, useState } from 'react';
import Icon from './components/Icon';
import MarketList from './components/MarketList';
import NewsFeed from './components/NewsFeed';
import StarDetails from './components/StarDetails';
import { useLiveMarket } from './market/useLiveMarket';

export default function App() {
  const { market, status, error, retry } = useLiveMarket();
  const [selectedAssetId, setSelectedAssetId] = useState<string>();
  const [selectedPlaceholder, setSelectedPlaceholder] = useState(0);
  const assets = market?.assets;
  const selectedAsset = assets?.find((asset) => asset.id === selectedAssetId)
    ?? (assets ? [...assets].sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))[0] : undefined);

  useEffect(() => {
    setSelectedAssetId((current) => assets?.some((asset) => asset.id === current)
      ? current
      : assets ? [...assets].sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))[0]?.id : undefined);
  }, [assets]);

  function selectAsset(id: string) {
    if (!assets?.some((asset) => asset.id === id)) return;
    setSelectedAssetId(id);
  }

  return (
    <div className="exchange-app" data-connection={status}>
      <a className="skip-link" href="#market">Skip to the market</a>
      <header className="app-header">
        <a className="brand" href="#market" aria-label="Star Market home"><span className="brand-mark"><Icon name="orbit" size={30} /></span><span>star<span className="brand-light">market</span><span className="brand-dot">.</span></span></a>
        <span className="header-divider" /><span className="header-caption">The stellar exchange</span>
        <div className="header-status" role="status"><span className="status-dot" /><span>{status === 'live' ? 'Live market' : status === 'connecting' ? 'Connecting' : status === 'reconnecting' ? 'Reconnecting' : 'Offline'}</span></div>
      </header>
      <main className="workspace">
        <div className="page-heading"><div><p className="section-kicker">A different kind of market</p><h1>Keep your eyes on the stars<span>.</span></h1></div><p className="page-description">Follow the market. Read the signals.<br />Find your next move.</p></div>
        {status !== 'live' && <div className="connection-banner" role="status"><span className="small-dot" /><p>{status === 'connecting' ? 'Connecting to the market…' : market ? 'Connection interrupted. Showing the last received prices.' : 'The market feed is unavailable. Try reconnecting.'}</p>{(status === 'offline' || status === 'reconnecting') && <button type="button" onClick={retry}>Reconnect <Icon name="arrow-right" size={13} /></button>}</div>}
        {status === 'live' && error && <div className="connection-banner" role="status"><p>{error}</p><button type="button" onClick={retry}>Retry <Icon name="arrow-right" size={13} /></button></div>}
        <div className="terminal-layout">
          <MarketList assets={assets} selectedAssetId={selectedAsset?.id} selectedPlaceholder={selectedPlaceholder} onSelect={selectAsset} onSelectPlaceholder={setSelectedPlaceholder} />
          <NewsFeed items={market?.news} onSelectAsset={selectAsset} />
          <StarDetails asset={selectedAsset} />
        </div>
        <footer className="workspace-footer"><span><Icon name="orbit" size={13} /> {market ? `Simulation tick ${market.tick}` : 'An entire universe of possibility.'}</span><span>STAR MARKET <span className="footer-cross">✦</span> OBSERVE. ANTICIPATE. TRADE.</span></footer>
      </main>
    </div>
  );
}
