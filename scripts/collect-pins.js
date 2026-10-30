() => {
  const found = new Map();
  for (const card of document.querySelectorAll('[data-test-id="pin"]')) {
    const cardId = card.getAttribute('data-test-pin-id') || '';
    if (/^Ad[A-Za-z0-9_-]+$/.test(cardId) || card.getAttribute('data-pl-hidden') === 'true') continue;
    const hasAdLabel = [...card.querySelectorAll('div,span')].some(e =>
      e.childElementCount === 0 && !e.closest('h1,h2,h3') &&
      /^(patrocinado(?: por.*)?|promovido(?: por.*)?|sponsored(?: by.*)?|promoted(?: by.*)?|anúncio)$/i.test(e.textContent.trim()));
    if (hasAdLabel) continue;
    const anchor = card.querySelector('a[href*="/pin/"]');
    if (!anchor) continue;
    const url = new URL(anchor.getAttribute('href'), location.origin);
    if (!(url.hostname === 'pinterest.com' || url.hostname.endsWith('.pinterest.com'))) continue;
    const pinId = /\/pin\/(?:[^/]*--)?(\d+)(?:\/|$)/.exec(url.pathname)?.[1];
    if (!pinId || found.has(pinId)) continue;
    const image = card.querySelector('img');
    const badge = card.querySelector('[data-test-id="PinTypeIdentifier"]')?.textContent.trim() ?? '';
    const title = card.querySelector('h2,h3')?.textContent.trim() ||
      (anchor.getAttribute('aria-label') ?? '').replace(/^Página do Pin\s*/i, '');
    let preview = image?.currentSrc || image?.src || null;
    if (preview) {
      try {
        const p = new URL(preview);
        if (p.protocol !== 'https:' || !(p.hostname === 'pinimg.com' || p.hostname.endsWith('.pinimg.com'))) preview = null;
      } catch { preview = null; }
    }
    found.set(pinId, {
      pinId, url: url.origin + '/pin/' + pinId + '/', title,
      preview,
      video: !!card.querySelector('video,[data-test-id^="pincard-video"]') || /^(?:\d+:){1,2}\d{2}$/.test(badge)
    });
    if (found.size >= 50) break;
  }
  return { url: location.href, scrollY, pins: [...found.values()] };
}
