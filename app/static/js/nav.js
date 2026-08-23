// Falls back through YouTube thumbnail candidates when the primary thumbnail fails to load.
(function () {
  document.querySelectorAll('img[data-thumb-candidates]').forEach(function (img) {
    var candidates = (img.getAttribute('data-thumb-candidates') || '').split(',').filter(Boolean);
    var fallback = img.getAttribute('data-fallback-src') || '';
    var index = 0;
    img.addEventListener('error', function () {
      if (index < candidates.length) {
        img.src = candidates[index];
        index += 1;
      } else if (fallback && img.src !== fallback) {
        img.src = fallback;
      }
    });
  });
})();
