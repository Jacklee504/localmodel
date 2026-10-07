const assert = require('node:assert/strict');
const test = require('node:test');
const { createSearch } = require('./search');

test('newer response wins and previous request is aborted', async () => {
  const pending = [];
  const search = createSearch((url, options) => new Promise(resolve => pending.push({ url, options, resolve })));
  const first = search.search('old');
  const second = search.search('new');
  assert.equal(pending[0].options.signal.aborted, true);
  pending[1].resolve({ json: async () => ['new'] });
  await second;
  pending[0].resolve({ json: async () => ['old'] });
  await first;
  assert.deepEqual(search.results, ['new']);
});

test('rejected request settles without throwing', async () => {
  const search = createSearch(async () => { throw new Error('offline'); });
  await search.search('x');
  assert.deepEqual(search.results, []);
});
