import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  applyMarketTick,
  createMarketState,
  mergeAssetHistory,
  parseHistory,
  parseSnapshot,
  parseTickMessage,
} from '../src/market/backend.ts';

function snapshot(t = 10, price = 500) {
  return parseSnapshot({
    t,
    assets: [{
      id: 'real-server-id', name: 'Server star', kind: 'star', stage: 'main_sequence',
      spectral_type: 'G', mass: 1, temperature: 5800, L: 1, price,
      shares_total: 1000, shares_available: 1000,
    }],
    leaderboard: [],
    news: [],
  });
}

function update(t: number, price: number, stage = 'main_sequence') {
  const message = parseTickMessage({ type: 'tick', t, assets: [{ id: 'real-server-id', stage, price, L: 2 }] });
  assert.ok(message);
  return message;
}

test('snapshot uses actual backend metadata and starts without a fabricated price baseline', () => {
  const state = createMarketState(snapshot(), 1234);
  const asset = state.market.assets[0];
  assert.equal(state.market.tick, 10);
  assert.equal(state.market.updatedAt, 1234);
  assert.deepEqual(state.market.news, []);
  assert.equal(state.market.newsError, undefined);
  assert.equal(asset.symbol, 'real-server-id');
  assert.equal(asset.stage, 'main_sequence');
  assert.equal(asset.classification, 'Main sequence');
  assert.equal(asset.spectralType, 'G');
  assert.equal(asset.temperature, 5800);
  assert.equal(asset.previousPrice, null);
  assert.equal(asset.previousChange, null);
  assert.equal(asset.radius, undefined);
  assert.equal(asset.description, undefined);
  assert.deepEqual(state.pointsByAsset.get(asset.id), [{ t: 10, price: 500 }]);
});

test('new ticks retain birth data while changing lifecycle, prices and prior observed changes', () => {
  const initial = createMarketState(snapshot());
  const first = applyMarketTick(initial, update(11, 510, 'red_giant'), 1300);
  const second = applyMarketTick(first, update(12, 508, 'supernova'), 1400);
  assert.equal(first.market.assets[0].previousPrice, 500);
  assert.equal(first.market.assets[0].previousChange, null);
  const asset = second.market.assets[0];
  assert.equal(asset.price, 508);
  assert.equal(asset.previousPrice, 510);
  assert.equal(asset.previousChange, 10);
  assert.equal(asset.stage, 'supernova');
  assert.equal(asset.classification, 'Supernova');
  assert.equal(asset.luminosity, 2);
  assert.equal(asset.spectralType, 'G');
  assert.equal(asset.mass, 1);
  assert.equal(asset.temperature, 5800);
  assert.equal(second.market.updatedAt, 1400);
  assert.notEqual(first.market.assets[0].color, initial.market.assets[0].color);
  assert.equal(initial.market.assets[0].price, 500);
});

test('every backend lifecycle stage works in snapshots and live tick updates', () => {
  const lifecycle = readFileSync(new URL('../../backend/app/lifecycle.py', import.meta.url), 'utf8');
  const stageLiteral = lifecycle.match(/^Stage\s*=\s*Literal\[([\s\S]*?)\]/m);
  assert.ok(stageLiteral, 'Backend lifecycle must declare its Stage literal.');
  const backendStages = [...stageLiteral[1].matchAll(/["']([^"']+)["']/g)].map((match) => match[1]);
  assert.ok(backendStages.length > 0, 'Backend Stage literal must contain lifecycle stages.');

  let live = createMarketState(snapshot());
  for (const [index, stage] of backendStages.entries()) {
    const expectedLabel = stage.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
    const parsed = parseSnapshot({ ...snapshot(), assets: [{ ...snapshot().assets[0], stage }] });
    const initial = createMarketState(parsed).market.assets[0];
    assert.equal(initial.stage, stage);
    assert.equal(initial.classification, expectedLabel);
    assert.match(initial.color, /^#[0-9a-f]{6}$/i);

    live = applyMarketTick(live, update(11 + index, 510 + index, stage));
    assert.equal(live.market.assets[0].stage, stage);
    assert.equal(live.market.assets[0].classification, expectedLabel);
    assert.equal(live.market.assets[0].color, initial.color);
  }

  assert.throws(() => update(99, 600, 'red_supergiant'), /unsupported stellar stage/);
  assert.throws(() => update(99, 600, 'unknown_stage'), /unsupported stellar stage/);
});

test('duplicate and out-of-order messages do not regress prices, baselines or chart state', () => {
  const state = applyMarketTick(createMarketState(snapshot()), update(12, 508));
  assert.equal(applyMarketTick(state, update(12, 999)), state);
  assert.equal(applyMarketTick(state, update(11, 999)), state);
  assert.equal(applyMarketTick(state, update(0, 999)), state);
});

test('history response races preserve live samples and clip points newer than the current tick', () => {
  const live = applyMarketTick(createMarketState(snapshot()), update(11, 510));
  const merged = mergeAssetHistory(live, 'real-server-id', [
    { t: 11, price: 999 }, { t: 9, price: 490 }, { t: 10, price: 998 }, { t: 12, price: 997 },
  ]);
  assert.deepEqual(merged.pointsByAsset.get('real-server-id'), [
    { t: 9, price: 490 }, { t: 10, price: 500 }, { t: 11, price: 510 },
  ]);
  assert.equal(merged.market.tick, 11);
  assert.equal(merged.market.assets[0].price, 510);
  assert.equal(merged.market.assets[0].previousPrice, 500);
  assert.deepEqual(live.pointsByAsset.get('real-server-id'), [{ t: 10, price: 500 }, { t: 11, price: 510 }]);
});

test('fresh lower-tick snapshot discards old-session history and comparisons', () => {
  const old = applyMarketTick(createMarketState(snapshot(500, 800)), update(501, 900));
  const restarted = createMarketState(snapshot(0, 100));
  assert.equal(old.market.tick, 501);
  assert.equal(restarted.market.tick, 0);
  assert.equal(restarted.market.assets[0].previousPrice, null);
  assert.equal(restarted.market.assets[0].previousChange, null);
  assert.deepEqual(restarted.pointsByAsset.get('real-server-id'), [{ t: 0, price: 100 }]);
  assert.throws(() => mergeAssetHistory(old, 'real-server-id', [{ t: 0, price: 100 }]), /server restarted/);
});

test('history remains bounded to the server retention length as ticks accumulate', () => {
  let state = createMarketState(snapshot(0));
  for (let t = 1; t <= 650; t += 1) state = applyMarketTick(state, update(t, 500 + t));
  const points = state.pointsByAsset.get('real-server-id');
  assert.equal(points?.length, 600);
  assert.equal(points?.[0].t, 51);
  assert.equal(points?.at(-1)?.t, 650);
});

test('protocol validation rejects unusable numbers and duplicate IDs', () => {
  assert.throws(() => parseSnapshot({ ...snapshot(), t: 1.5 }), /integer/);
  assert.throws(() => parseSnapshot({ ...snapshot(), t: '1' }), /finite number/);
  assert.throws(() => parseSnapshot({ ...snapshot(), assets: [snapshot().assets[0], snapshot().assets[0]] }), /duplicate/);
  assert.throws(() => parseTickMessage({ type: 'tick', t: 2, assets: [{ id: 'id', stage: 'main_sequence', price: Infinity, L: 1 }] }), /finite number/);
  assert.throws(() => parseHistory([{ t: -1, price: 1 }]), /finite number/);
  assert.throws(() => parseHistory([{ t: 1, price: '2' }]), /finite number/);
  assert.throws(() => parseHistory({ points: [] }), /expected a list/);
  assert.deepEqual(parseHistory([{ t: 1, price: 0 }]), [{ t: 1, price: 0 }]);
  assert.equal(parseTickMessage({ type: 'leaderboard', rows: [] }), null);
});

test('unknown asset delta requests a new authoritative snapshot', () => {
  const message = update(11, 600);
  message.assets[0].id = 'new-server-asset';
  assert.throws(() => applyMarketTick(createMarketState(snapshot()), message), /fresh snapshot/);
});
