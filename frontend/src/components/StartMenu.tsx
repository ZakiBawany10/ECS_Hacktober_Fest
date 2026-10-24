import { useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { PlayerSession } from '../player/usePlayerSession';
import Icon from './Icon';
import './StartMenu.css';

interface StartMenuProps {
  session: PlayerSession;
  onStart: (nickname: string) => Promise<boolean>;
  onResume: () => Promise<boolean>;
}

export default function StartMenu({ session, onStart, onResume }: StartMenuProps) {
  const id = useId();
  const [nickname, setNickname] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const submittingRef = useRef(false);
  const busy = submitting || session.busy !== null || session.syncing;
  const trimmedName = nickname.trim();
  const validName = trimmedName.length > 0 && Array.from(trimmedName).length <= 20;

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || submittingRef.current || (!session.hasSession && !validName)) return;
    submittingRef.current = true;
    setSubmitting(true);
    setSubmissionError(null);
    try {
      if (session.hasSession) await onResume();
      else await onStart(trimmedName);
    } catch {
      setSubmissionError('Unable to open the market. Check your connection and try again.');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <div className="start-menu">
      <header className="start-menu-header">
        <span className="brand" aria-label="Star Market">
          <span className="brand-mark"><Icon name="orbit" size={30} /></span>
          <span>star<span className="brand-light">market</span><span className="brand-dot">.</span></span>
        </span>
        <span className="start-menu-edition">The stellar exchange</span>
      </header>
      <main className="start-menu-main" aria-labelledby={`${id}-title`}>
        <div className="start-menu-intro">
          <p className="start-menu-kicker"><span /> A different kind of market</p>
          <h1 id={`${id}-title`}>Your next move.<br />An entire <span>universe.</span></h1>
          <p className="start-menu-description">Follow the stars. Read the signals. Trade your way through a universe that keeps changing.</p>
          <div className="start-menu-orbit" aria-hidden="true">
            <span className="start-orbit-ring start-orbit-ring-outer" />
            <span className="start-orbit-ring start-orbit-ring-middle" />
            <span className="start-orbit-ring start-orbit-ring-inner" />
            <span className="start-orbit-core" />
            <span className="start-orbit-planet start-orbit-planet-one" />
            <span className="start-orbit-planet start-orbit-planet-two" />
            <span className="start-orbit-cross">✦</span>
          </div>
        </div>
        <section className="start-menu-card" aria-labelledby={`${id}-form-title`} aria-busy={busy}>
          <div className="start-menu-card-icon"><Icon name="orbit" size={25} /></div>
          <p className="section-kicker">{session.hasSession ? 'Welcome back' : 'Ready when you are'}</p>
          <h2 id={`${id}-form-title`}>{session.hasSession ? 'Back to the stars.' : 'Enter the exchange.'}</h2>
          <p className="start-menu-card-description">{session.hasSession ? 'Your player is saved on this browser. Resume to return to your portfolio and the live market.' : 'Choose your name, then start the simulation and make your first move.'}</p>
          <form className="start-menu-form" aria-labelledby={`${id}-form-title`} onSubmit={start}>
            {!session.hasSession && <>
              <label htmlFor={`${id}-nickname`}>Your name</label>
              <input id={`${id}-nickname`} name="nickname" type="text" autoComplete="nickname" maxLength={20} required value={nickname} disabled={busy} placeholder="Your name" aria-describedby={`${id}-name-help`} onChange={(event) => { setNickname(event.target.value); setSubmissionError(null); }} />
              <p className="start-menu-name-help" id={`${id}-name-help`}>1–20 characters. This is how you appear in the market.</p>
            </>}
            <button type="submit" disabled={busy || (!session.hasSession && !validName)}>
              <span>{busy ? session.hasSession ? 'Resuming…' : 'Starting…' : session.hasSession ? 'Resume simulation' : 'Start simulation'}</span>
              <Icon name="arrow-right" size={18} />
            </button>
            {(submissionError || session.error) && <p className="start-menu-error" role="alert">{submissionError || session.error}</p>}
            {session.notice && <p className="start-menu-notice" role="status">{session.notice}</p>}
          </form>
          <a className="start-menu-help" href="/how-to-play.html" target="_blank" rel="noreferrer" aria-label="How to play (opens in a new tab)">How to play ↗</a>
          <p className="start-menu-card-footer"><Icon name="signal" size={14} /> A shared universe. Every decision counts.</p>
        </section>
      </main>
      <footer className="start-menu-footer"><span>STAR MARKET</span><span>OBSERVE. ANTICIPATE. TRADE.</span></footer>
    </div>
  );
}
