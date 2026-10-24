import { useEffect, useRef, useState } from 'react';
import type { StarAsset } from '../market/types';
import './DemoControls.css';

interface DemoControlsProps {
  asset?: StarAsset;
  connected: boolean;
}

export default function DemoControls({ asset, connected }: DemoControlsProps) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const uncertain = useRef(false);
  const [blocked, setBlocked] = useState(false);
  const terminal = asset && ['black_hole', 'neutron_star', 'white_dwarf'].includes(asset.stage);

  useEffect(() => () => {
    const controller = request.current;
    request.current = null;
    controller?.abort();
  }, []);

  async function advance() {
    if (!asset || !connected || terminal || lock.current || uncertain.current) return;
    lock.current = true;
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    setPending(true);
    setMessage(null);
    try {
      const response = await fetch(`${import.meta.env.DEV ? '/api' : ''}/director/force_stage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset_id: asset.id }), signal: controller.signal,
      });
      if (response.status >= 500) throw new Error('The stage change could not be confirmed.');
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
        setMessage(typeof detail === 'string' ? detail : 'Unable to advance this star.');
        return;
      }
      setMessage(`${asset.name} advanced. Its new stage appears with the next market update.`);
    } catch {
      if (request.current !== controller) return;
      uncertain.current = true;
      setBlocked(true);
      setMessage('The result is uncertain. Check the star’s stage before reloading these demo controls.');
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        lock.current = false;
        setPending(false);
      }
    }
  }

  return (
    <section className="demo-controls" aria-label="Demo controls">
      <div><p className="section-kicker">Demo controls</p><p>Move the selected star to its next stage.</p></div>
      <button type="button" disabled={!asset || !connected || terminal || pending || blocked} onClick={() => void advance()}>{pending ? 'Advancing…' : terminal ? 'Final stage reached' : `Advance ${asset?.name ?? 'selected star'}`}</button>
      {message && <p className="demo-message" role="status">{message}</p>}
    </section>
  );
}
