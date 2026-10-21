const assert = require('node:assert/strict');
const test = require('node:test');
const { createSearch } = require('./search');

test('a third request aborts the second', async () => {
  const pending = [];
  const search = createSearch((url, options) => new Promise(resolve => pending.push({ url, options, resolve })));
  const first = search.search('a');
  const second = search.search('b');
  const third = search.search('c');
  assert.equal(pending[0].options.signal.aborted, true);
  assert.equal(pending[1].options.signal.aborted, true);
  pending[2].resolve({ json: async () => ['c'] });
  await third;
  assert.deepEqual(search.results, ['c']);
});

test('results stay unchanged when the newest request fails', async () => {
  const search = createSearch(async () => { throw new Error('offline'); });
  await search.search('x');
  assert.deepEqual(search.results, []);
});

test('a successful earlier request does not overwrite a newer one', async () => {
  const pending = [];
  const search = createSearch((url, options) => new Promise(resolve => pending.push({ url, options, resolve })));
  const first = search.search('old');
  const second = search.search('new');
  pending[1].resolve({ json: async () => ['new'] });
  await second;
  pending[0].resolve({ json: async () => ['old'] });
  await first;
  assert.deepEqual(search.results, ['new']);
});
