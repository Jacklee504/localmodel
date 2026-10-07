function createSearch(fetcher) {
  let results = [];
  return {
    get results() { return results; },
    async search(query) {
      const response = await fetcher('/api/search?q=' + encodeURIComponent(query));
      results = await response.json();
    }
  };
}
module.exports = { createSearch };
