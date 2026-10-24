import { useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { StarAsset } from '../market/types';
import type { Portfolio } from '../player/api';
import './TradeTicket.css';

interface TradeTicketProps {
  asset?: StarAsset;
  portfolio?: Portfolio;
  hasSession: boolean;
  disabled: boolean;
  busy: boolean;
  feedback?: string | null;
  feedbackError?: boolean;
  onTrade: (assetId: string, side: 'buy' | 'sell', qty: number) => Promise<boolean>;
}

const CREDITS = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const SHARES = new Intl.NumberFormat('en-GB', { maximumSignificantDigits: 10 });

export default function TradeTicket({ asset, portfolio, hasSession, disabled, busy, feedback, feedbackError, onTrade }: TradeTicketProps) {
  const id = useId();
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState('');
  const submittingRef = useRef(false);
  const held = asset && portfolio ? (portfolio.holdings[asset.id] ?? 0) : 0;
  const qty = Number(quantity);
  const validQuantity = quantity.trim() !== '' && Number.isFinite(qty) && qty > 0;
  const estimate = asset && validQuantity ? asset.price * qty : undefined;
  const validEstimate = estimate !== undefined && Number.isFinite(estimate);
  const blackHole = asset?.stage === 'black_hole';
  const pending = busy || submitting;
  const controlsDisabled = !asset || !hasSession || !portfolio || disabled || pending || blackHole;
  const exceedsHoldings = side === 'sell' && validQuantity && qty > held;
  const canSubmit = !controlsDisabled && validQuantity && validEstimate && !exceedsHoldings && (side !== 'sell' || held > 0);
  const status = !asset ? 'Select a star to trade.'
    : blackHole ? 'Trading closed: black holes cannot be traded.'
      : !hasSession ? 'Join the market to place an order.'
        : !portfolio ? 'Loading your holdings…'
          : pending ? 'Updating your portfolio…'
            : disabled ? 'Trading is paused until the connection and portfolio are up to date.'
              : side === 'sell' && held <= 0 ? 'You do not own shares in this star.'
                : exceedsHoldings ? 'Quantity exceeds your available shares.'
                  : quantity !== '' && !validQuantity ? 'Enter a positive, finite quantity.'
                    : estimate !== undefined && !validEstimate ? 'This quantity is too large.'
                      : '';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || !asset || submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setSubmissionError('');
    try {
      if (await onTrade(asset.id, side, qty)) setQuantity('');
    } catch {
      setSubmissionError('Unable to confirm the order. Refresh your portfolio before trying again.');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <section className="trade-ticket" aria-labelledby={`${id}-title`} aria-busy={pending}>
      <div className="trade-ticket-heading">
        <h3 id={`${id}-title`}>Place an order</h3>
        <p>Your shares <strong>{portfolio && asset ? SHARES.format(held) : '—'}</strong></p>
      </div>
      <form onSubmit={submit}>
        <div className="trade-side" role="group" aria-label="Order side">
          <button type="button" aria-pressed={side === 'buy'} disabled={controlsDisabled} onClick={() => { setSide('buy'); setSubmissionError(''); }}>Buy</button>
          <button type="button" aria-pressed={side === 'sell'} disabled={controlsDisabled || held <= 0} onClick={() => { setSide('sell'); setSubmissionError(''); }}>Sell</button>
        </div>
        <label className="trade-quantity" htmlFor={`${id}-quantity`}>
          <span>Quantity <span>Fractional shares allowed</span></span>
          <input id={`${id}-quantity`} type="number" inputMode="decimal" step="any" min="0" required value={quantity} disabled={controlsDisabled} placeholder="{quantity}" aria-describedby={`${id}-status ${id}-estimate-note`} onChange={(event) => { setQuantity(event.target.value); setSubmissionError(''); }} />
        </label>
        <dl className="trade-estimate">
          <div><dt>Estimated {side === 'buy' ? 'cost' : 'proceeds'}</dt><dd>{validEstimate ? `${CREDITS.format(estimate)} CR` : '—'}</dd></div>
        </dl>
        <p className="trade-estimate-note" id={`${id}-estimate-note`}>Based on the latest quote. Your order affects its execution price; the server sets the final amount.</p>
        <p className="trade-ticket-status" id={`${id}-status`} role="status">{submissionError || status}</p>
        {feedback && <p className={`trade-feedback${feedbackError ? ' trade-feedback-error' : ''}`} role="status">{feedback}</p>}
        <button className={`trade-submit trade-submit-${side}`} type="submit" disabled={!canSubmit}>{pending ? 'Submitting…' : `${side === 'buy' ? 'Buy' : 'Sell'} shares`}</button>
      </form>
    </section>
  );
}
