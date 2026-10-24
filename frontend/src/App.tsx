import { useEffect, useState } from 'react';
import Icon from './components/Icon';
import MarketList from './components/MarketList';
import NewsFeed from './components/NewsFeed';
import StarDetails from './components/StarDetails';
import PlayerPanel from './components/PlayerPanel';
import TradeTicket from './components/TradeTicket';
import DemoControls from './components/DemoControls';
import StartMenu from './components/StartMenu';
import { useLiveMarket } from './market/useLiveMarket';
import { usePlayerSession } from './player/usePlayerSession';

export default function App() {
  const [entered, setEntered] = useState(false);
  const { market, status, error, retry } = useLiveMarket(entered);
  const session = usePlayerSession(status);
  const [directorEnabled] = useState(() => new URLSearchParams(window.location.search).get('director') === '1');
  const [selectedAssetId, setSelectedAssetId] = useState<string>();
  const [orderAssetId, setOrderAssetId] = useState<string>();
  const [openStory, setOpenStory] = useState<{ id: string; request: number }>();
  const [activeNewsId, setActiveNewsId] = useState<string | null>(null);
  const [selectedPlaceholder, setSelectedPlaceholder] = useState(0);
  const assets = market?.assets;
  const selectedAsset = assets?.find((asset) => asset.id === selectedAssetId)
    ?? (assets ? [...assets].sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))[0] : undefined);

  useEffect(() => {
    if (entered && !session.hasSession) {
      setEntered(false);
      setSelectedAssetId(undefined);
      setOrderAssetId(undefined);
      setOpenStory(undefined);
      setActiveNewsId(null);
    }
  }, [entered, session.hasSession]);

  useEffect(() => {
    setSelectedAssetId((current) => assets?.some((asset) => asset.id === current)
      ? current
      : assets ? [...assets].sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))[0]?.id : undefined);
  }, [assets]);

  function selectAsset(id: string) {
    if (!assets?.some((asset) => asset.id === id)) return;
    setSelectedAssetId(id);
  }

  async function placeOrder(assetId: string, side: 'buy' | 'sell', quantity: number) {
    setOrderAssetId(assetId);
    return session.trade(assetId, side, quantity);
  }

  function openNews(id: string) {
    if (!market?.news?.some((item) => item.id === id)) return;
    setActiveNewsId(id);
    setOpenStory((previous) => ({ id, request: (previous?.request ?? 0) + 1 }));
  }

  async function startSimulation(nickname: string) {
    const joined = await session.join(nickname);
    if (joined) setEntered(true);
    return joined;
  }

  async function resumeSimulation() {
    const restored = await session.resume();
    if (restored) setEntered(true);
    return restored;
  }

  if (!entered || !session.hasSession) {
    return <StartMenu session={session} onStart={startSimulation} onResume={resumeSimulation} />;
  }

  return (
    <div className="exchange-app" data-connection={status}>
      <a className="skip-link" href="#market">Skip to the market</a>
      <header className="app-header">
        <a className="brand" href="#market" aria-label="Star Market home"><span className="brand-mark"><Icon name="orbit" size={30} /></span><span>star<span className="brand-light">market</span><span className="brand-dot">.</span></span></a>
        <span className="header-divider" /><span className="header-caption">The stellar exchange</span>
        <a className="market-help-link" href="/how-to-play.html" target="_blank" rel="noreferrer" aria-label="How to play (opens in a new tab)">Help ↗</a>
        <div className="header-status" role="status"><span className="status-dot" /><span>{status === 'live' ? 'Live market' : status === 'connecting' ? 'Connecting' : status === 'reconnecting' ? 'Reconnecting' : 'Offline'}</span></div>
      </header>
      <main className="workspace">
        <div className="page-heading"><div><p className="section-kicker">A different kind of market</p><h1>Keep your eyes on the stars<span>.</span></h1></div><p className="page-description">Follow the market. Read the signals.<br />Find your next move.</p></div>
        {status !== 'live' && <div className="connection-banner" role="status"><span className="small-dot" /><p>{status === 'connecting' ? 'Connecting to the market…' : market ? 'Connection interrupted. Showing the last received prices.' : 'The market feed is unavailable. Try reconnecting.'}</p>{(status === 'offline' || status === 'reconnecting') && <button type="button" onClick={retry}>Reconnect <Icon name="arrow-right" size={13} /></button>}</div>}
        {status === 'live' && error && <div className="connection-banner" role="status"><p>{error}</p><button type="button" onClick={retry}>Retry <Icon name="arrow-right" size={13} /></button></div>}
        <PlayerPanel session={session} assets={assets} connected={status === 'live'} onSelectAsset={selectAsset} />
        {directorEnabled && <DemoControls key={selectedAsset?.id} asset={selectedAsset} connected={status === 'live'} />}
        <div className="terminal-layout">
          <MarketList assets={assets} selectedAssetId={selectedAsset?.id} selectedPlaceholder={selectedPlaceholder} onSelect={selectAsset} onSelectPlaceholder={setSelectedPlaceholder} />
          <NewsFeed items={market?.news} assets={assets} status={status} error={market?.newsError} onRetry={retry} onSelectAsset={selectAsset} openStory={openStory} onExpandedNewsChange={setActiveNewsId} />
          <StarDetails asset={selectedAsset} news={market?.news} currentTick={market?.tick} activeNewsId={activeNewsId ?? undefined} onSelectNews={openNews}>
            <TradeTicket key={selectedAsset?.id ?? 'empty'} asset={selectedAsset} portfolio={session.portfolio} hasSession={session.hasSession} busy={session.busy === 'trade'} disabled={status !== 'live' || session.stale || session.busy !== null} onTrade={placeOrder} feedback={orderAssetId === selectedAsset?.id ? session.error ?? session.notice : null} feedbackError={Boolean(session.error)} />
          </StarDetails>
        </div>
        <footer className="workspace-footer"><span><Icon name="orbit" size={13} /> {market ? `Simulation tick ${market.tick}` : 'An entire universe of possibility.'}</span><span>STAR MARKET <span className="footer-cross">✦</span> OBSERVE. ANTICIPATE. TRADE.</span></footer>
      </main>
    </div>
  );
}
