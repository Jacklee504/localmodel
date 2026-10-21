import assert from 'node:assert/strict';
import test from 'node:test';
import { normaliseDeal, normaliseText, dealFingerprint } from '../matching.ts';

test('normaliseText lowercases, collapses whitespace and trims', () => {
  assert.equal(normaliseText('  Hello   WORLD  '), 'hello world');
  assert.equal(normaliseText('a\t\tb'), 'a b');
  assert.equal(normaliseText(''), '');
});

test('normaliseDeal normalises title and company', () => {
  const deal = normaliseDeal({ title: '  Acme  Corp  ', company: 'ACME   Ltd' });
  assert.equal(deal.title, 'acme corp');
  assert.equal(deal.company, 'acme ltd');
});

test('normaliseDeal keeps amount and url behaviour', () => {
  const deal = normaliseDeal({ amount: '1200', url: 'http://x' });
  assert.equal(deal.amount, 1200);
  assert.equal(deal.url, 'http://x');
});

test('missing fields keep their defaults', () => {
  const deal = normaliseDeal({});
  assert.equal(deal.title, '');
  assert.equal(deal.company, '');
  assert.equal(deal.amount, 0);
  assert.equal(deal.url, '');
});

test('dealFingerprint joins normalised title and company', () => {
  const deal = normaliseDeal({ title: 'Acme Corp', company: 'Acme Ltd' });
  assert.equal(dealFingerprint(deal), 'acme corp|acme ltd');
});

test('dealFingerprint of an empty deal is a single separator', () => {
  assert.equal(dealFingerprint(normaliseDeal({})), '|');
});

test('deals differing only in whitespace share a fingerprint', () => {
  const first = normaliseDeal({ title: 'Acme  Corp', company: 'Acme Ltd' });
  const second = normaliseDeal({ title: 'acme corp', company: 'ACME   LTD' });
  assert.equal(dealFingerprint(first), dealFingerprint(second));
});
