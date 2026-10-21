import assert from 'node:assert/strict';
import test from 'node:test';
import { normaliseDeal, normaliseText, dealFingerprint } from '../matching.ts';

test('normaliseText collapses newlines and tabs', () => {
  assert.equal(normaliseText('a\n\nb\tc'), 'a b c');
});

test('normaliseText is idempotent', () => {
  const once = normaliseText('  Some   Thing  ');
  assert.equal(normaliseText(once), once);
});

test('dealFingerprint distinguishes different companies', () => {
  const first = normaliseDeal({ title: 'Acme', company: 'One' });
  const second = normaliseDeal({ title: 'Acme', company: 'Two' });
  assert.notEqual(dealFingerprint(first), dealFingerprint(second));
});

test('dealFingerprint distinguishes different titles', () => {
  const first = normaliseDeal({ title: 'One', company: 'Acme' });
  const second = normaliseDeal({ title: 'Two', company: 'Acme' });
  assert.notEqual(dealFingerprint(first), dealFingerprint(second));
});

test('normaliseDeal does not alter the amount when it is absent', () => {
  assert.equal(normaliseDeal({ title: 'x' }).amount, 0);
});

test('normaliseDeal lowercases a mixed case title', () => {
  assert.equal(normaliseDeal({ title: 'MiXeD' }).title, 'mixed');
});
