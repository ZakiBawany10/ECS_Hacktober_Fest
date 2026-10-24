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
const BUY_QUANTITIES = [1, 5, 10, 25];

export default function TradeTicket({ asset, portfolio, hasSession, disabled, busy, feedback, feedbackError, onTrade }: TradeTicketProps) {
  const id = useId();
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [buyQuantity, setBuyQuantity] = useState('');
  const [sellQuantity, setSellQuantity] = useState<string | null>(null);
  const [manualSell, setManualSell] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState('');
  const submittingRef = useRef(false);
  const held = asset && portfolio ? (portfolio.holdings[asset.id] ?? 0) : 0;
  const usingSellSlider = side === 'sell' && held >= 1 && !manualSell;
  const enteredSellQuantity = sellQuantity ?? (held > 0 ? String(Math.min(1, held)) : '');
  const sliderQuantity = Math.min(held, Math.max(1, Number(enteredSellQuantity) || 1));
  const quantity = side === 'buy' ? buyQuantity : usingSellSlider ? String(sliderQuantity) : enteredSellQuantity;
  const qty = Number(quantity);
  const validQuantity = quantity.trim() !== '' && Number.isFinite(qty) && qty > 0;
  const estimate = asset && validQuantity ? asset.price * qty : undefined;
  const validEstimate = estimate !== undefined && Number.isFinite(estimate);
  const blackHole = asset?.stage === 'black_hole';
  const pending = busy || submitting;
  const controlsDisabled = !asset || !hasSession || !portfolio || disabled || pending || blackHole;
  const exceedsHoldings = side === 'sell' && validQuantity && qty > held;
  const exceedsCash = side === 'buy' && validEstimate && portfolio !== undefined && estimate > portfolio.cash;
  const canSubmit = !controlsDisabled && validQuantity && validEstimate && !exceedsHoldings && !exceedsCash && (side !== 'sell' || held > 0);
  const status = !asset ? 'Select a star to trade.'
    : blackHole ? 'Trading closed: black holes cannot be traded.'
      : !hasSession ? 'Join the market to place an order.'
        : !portfolio ? 'Loading your holdings…'
          : pending ? 'Updating your portfolio…'
            : disabled ? 'Trading is paused until the connection and portfolio are up to date.'
              : side === 'sell' && held <= 0 ? 'You do not own shares in this star.'
                : exceedsHoldings ? 'Quantity exceeds your available shares.'
                  : exceedsCash ? 'Not enough cash for this quantity. Choose fewer shares.'
                    : quantity !== '' && !validQuantity ? 'Enter a positive, finite quantity.'
                      : estimate !== undefined && !validEstimate ? 'This quantity is too large.'
                        : '';

  function updateQuantity(value: string) {
    if (side === 'buy') setBuyQuantity(value);
    else setSellQuantity(value);
    setSubmissionError('');
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || !asset || submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setSubmissionError('');
    try {
      if (await onTrade(asset.id, side, qty)) {
        if (side === 'buy') setBuyQuantity('');
        else setSellQuantity(null);
      }
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
        {usingSellSlider ? (
          <div className="trade-sell-range">
            <div className="trade-range-heading">
              <label htmlFor={`${id}-sell-range`}>Shares to sell</label>
              <output htmlFor={`${id}-sell-range`}>{SHARES.format(qty)}</output>
            </div>
            <input id={`${id}-sell-range`} type="range" min="1" max={held} step="any" value={qty} disabled={controlsDisabled} aria-valuetext={`${SHARES.format(qty)} shares`} aria-describedby={`${id}-status ${id}-estimate-note`} onChange={(event) => updateQuantity(event.target.value)} />
            <div className="trade-range-bounds"><span>1 share</span><span>{SHARES.format(held)} available</span></div>
          </div>
        ) : (
          <label className="trade-quantity" htmlFor={`${id}-quantity`}>
            <span>Quantity <span>Fractional shares allowed</span></span>
            <input id={`${id}-quantity`} type="number" inputMode="decimal" step="any" min="0" max={side === 'sell' ? held : undefined} required value={quantity} disabled={controlsDisabled || (side === 'sell' && held <= 0)} placeholder="{quantity}" aria-invalid={exceedsCash || exceedsHoldings || (quantity !== '' && (!validQuantity || !validEstimate))} aria-describedby={`${id}-status ${id}-estimate-note`} onChange={(event) => updateQuantity(event.target.value)} />
          </label>
        )}
        {side === 'buy' ? (
          <div className="trade-buy-shortcuts" role="group" aria-label="Quick buy quantity">
            {BUY_QUANTITIES.map((amount) => {
              const unaffordable = asset !== undefined && portfolio !== undefined && amount * asset.price > portfolio.cash;
              return <button key={amount} type="button" disabled={controlsDisabled || unaffordable} title={unaffordable ? 'Not enough cash at the latest quote' : undefined} aria-label={`Set buy quantity to ${amount} shares`} aria-pressed={validQuantity && qty === amount} onClick={() => updateQuantity(String(amount))}>{amount}</button>;
            })}
          </div>
        ) : held >= 1 ? (
          <button className="trade-quantity-mode" type="button" disabled={controlsDisabled} onClick={() => {
            if (manualSell) setSellQuantity(String(sliderQuantity));
            setManualSell(!manualSell);
            setSubmissionError('');
          }}>{manualSell ? 'Use slider' : 'Enter quantity manually'}</button>
        ) : held > 0 ? (
          <p className="trade-fraction-note">You hold less than 1 share. Enter a fractional quantity to sell.</p>
        ) : null}
        <dl className="trade-estimate">
          {side === 'buy' && portfolio && <div><dt>Available cash</dt><dd>{CREDITS.format(portfolio.cash)} CR</dd></div>}
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
