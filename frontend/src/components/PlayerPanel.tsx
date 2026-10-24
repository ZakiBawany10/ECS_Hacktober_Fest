import { useState } from 'react';
import type { FormEvent } from 'react';
import type { usePlayerSession } from '../player/usePlayerSession';
import type { StarAsset } from '../market/types';
import './PlayerPanel.css';

interface PlayerPanelProps {
  session: ReturnType<typeof usePlayerSession>;
  assets?: StarAsset[];
  connected: boolean;
  onSelectAsset: (id: string) => void;
}

const CREDITS = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const QUANTITY = new Intl.NumberFormat('en-GB', { maximumSignificantDigits: 10 });

export default function PlayerPanel({ session, assets, connected, onSelectAsset }: PlayerPanelProps) {
  const [nickname, setNickname] = useState('');
  const { portfolio, hasSession, busy, syncing, stale, error, notice } = session;
  const holdings = Object.entries(portfolio?.holdings ?? {}).filter(([, quantity]) => quantity > 0);

  async function join(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!connected || busy || !nickname.trim()) return;
    await session.join(nickname.trim());
  }

  return (
    <section className="player-panel" aria-labelledby="player-title" aria-busy={busy !== null || syncing}>
      <div className="player-heading">
        <div><p className="section-kicker">Your position</p><h2 id="player-title">{portfolio ? portfolio.nickname : hasSession ? 'Your portfolio' : 'Join the exchange'}<span className="heading-dot">.</span></h2></div>
        {hasSession && <button className="player-refresh" type="button" disabled={syncing || busy !== null || !connected} onClick={session.refresh}>{syncing ? 'Refreshing…' : 'Refresh portfolio'}</button>}
      </div>
      {!hasSession && <form className="join-form" onSubmit={join}>
        <label htmlFor="player-nickname">Nickname</label>
        <input id="player-nickname" name="nickname" autoComplete="nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} maxLength={20} required disabled={busy !== null} placeholder="Your nickname" />
        <button className="player-primary" type="submit" disabled={!connected || busy !== null || !nickname.trim()}>{busy === 'join' ? 'Joining…' : 'Join market'}</button>
        {!connected && <p className="player-help">Connect to the market to join.</p>}
      </form>}
      {hasSession && !portfolio && <p className="player-help">{syncing ? 'Loading your portfolio…' : 'Your portfolio is unavailable. Reconnect and refresh to continue.'}</p>}
      {portfolio && <>
        <dl className="player-balances"><div><dt>Available cash</dt><dd>{CREDITS.format(portfolio.cash)} <span>CR</span></dd></div><div><dt>Net worth</dt><dd>{CREDITS.format(portfolio.net_worth)} <span>CR</span></dd></div></dl>
        <div className="player-holdings"><h3>Your holdings</h3>{holdings.length ? <ul>{holdings.map(([id, quantity]) => {
          const asset = assets?.find((star) => star.id === id);
          return <li key={id}><button type="button" onClick={() => onSelectAsset(id)} disabled={!asset}><span>{asset?.name ?? id}</span><strong>{QUANTITY.format(quantity)} shares</strong>{asset?.stage === 'black_hole' && <small>Not tradable</small>}</button></li>;
        })}</ul> : <p>No shares held yet. Select a star to place your first order.</p>}</div>
      </>}
      {hasSession && stale && portfolio && <p className="player-help">Showing the last received balance. Refresh successfully before trading.</p>}
      {error && <p className="player-message player-error" role="alert">{error}</p>}
      {notice && <p className="player-message" role="status">{notice}</p>}
    </section>
  );
}
