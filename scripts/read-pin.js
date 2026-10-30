async () => {
  const pinId = /\/pin\/(?:[^/]*--)?(\d+)(?:\/|$)/.exec(location.pathname)?.[1];
  if (!pinId || !(location.hostname === 'pinterest.com' || location.hostname.endsWith('.pinterest.com'))) {
    throw new Error('Open the Pinterest pin page before extracting media.');
  }
  let pin;
  for (const script of document.querySelectorAll('script[type="application/json"]')) {
    try {
      const data = JSON.parse(script.textContent);
      const candidate = data.initialReduxState?.pins?.[pinId] || data.resource_response?.data;
      if (String(candidate?.id) === pinId && (candidate.images || candidate.videos || candidate.story_pin_data)) {
        pin = candidate;
        if (pin.videos || pin.story_pin_data) break;
      }
    } catch { /* Other application data is irrelevant to this pin. */ }
  }
  const mainVideo = document.querySelector('[data-test-id="closeup-media-container"] video, [data-test-id="closeup-body-image-container"] video');
  if (!pin || (mainVideo && !pin.videos && !pin.story_pin_data)) {
    const endpoint = new URL('/resource/PinResource/get/', location.origin);
    endpoint.searchParams.set('data', JSON.stringify({ options: { id: pinId, field_set_key: 'unauth_react_main_pin' } }));
    const response = await fetch(endpoint, { credentials: 'include', headers: { 'X-Pinterest-PWS-Handler': 'www/[username].js' }, signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error('Pinterest did not provide the pin: HTTP ' + response.status);
    pin = (await response.json()).resource_response?.data;
  }
  if (String(pin?.id) !== pinId) throw new Error('The metadata ID does not match the current pin.');
  const safe = value => {
    try {
      const u = new URL(value);
      return u.protocol === 'https:' && !u.username && !u.password &&
        (u.hostname === 'pinimg.com' || u.hostname.endsWith('.pinimg.com'));
    } catch { return false; }
  };
  const imageVariants = Object.values(pin.images || {}).filter(i => safe(i?.url))
    .map(i => ({ url: i.url, width: i.width || 0, height: i.height || 0 }))
    .sort((a, b) => b.width * b.height - a.width * a.height);
  const lists = [pin.videos?.video_list];
  for (const page of pin.story_pin_data?.pages || []) {
    for (const block of page.blocks || []) lists.push(block.video?.video_list);
  }
  const seen = new Set();
  const formats = lists.flatMap(list => Object.values(list || {})).filter(f => {
    if (!safe(f?.url) || seen.has(f.url)) return false;
    seen.add(f.url); return true;
  }).map(f => ({ url: f.url, width: f.width || 0, height: f.height || 0, durationMs: f.duration ?? null }))
    .sort((a, b) => b.width * b.height - a.width * a.height);
  return {
    pinId, url: location.origin + '/pin/' + pinId + '/',
    title: pin.title || pin.grid_title || '',
    description: pin.description || '',
    pinnedBy: pin.pinner?.full_name || pin.pinner?.username || null,
    images: imageVariants, formats
  };
}
