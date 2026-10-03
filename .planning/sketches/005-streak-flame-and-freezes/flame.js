// Shared flame + freeze rendering and animation for sketches 005 and 006.
// Plain JS, no build step. Exposes window.Streak.

(function () {
  const C = {
    red: 'oklch(0.60 0.21 29)',
    orange: 'oklch(0.73 0.18 55)',
    yellow: 'oklch(0.90 0.15 95)',
    num: '#2b1400',
    ice: 'oklch(0.82 0.10 230)',
    iceBg: 'oklch(0.82 0.10 230 / 0.20)',
    grey: 'oklch(0.50 0 0)',
  };

  // One flame silhouette: rounded bowl, tip at top, a small lick on the left.
  const OUTER_A =
    'M50 4 C58 22 82 36 85 64 C88 94 70 116 50 116 C30 116 12 102 14 76 C15 60 24 50 30 40 C32 52 38 58 42 58 C38 40 42 20 50 4 Z';
  // Variant B: three distinct shapes with offset tips (more organic fire).
  const B_OUT =
    'M48 2 C60 20 86 36 86 66 C86 96 68 118 48 118 C26 118 10 100 12 76 C14 58 26 48 32 36 C34 48 40 54 44 54 C40 36 40 18 48 2 Z';
  const B_MID =
    'M58 28 C66 46 78 60 76 82 C74 104 62 114 48 114 C32 114 21 103 21 86 C21 72 32 62 38 50 C41 60 45 65 50 65 C49 52 52 40 58 28 Z';
  const B_IN =
    'M50 56 C58 70 66 80 64 94 C62 106 56 111 48 111 C38 111 31 104 31 93 C31 80 44 72 50 56 Z';
  // Variant C: chunky symmetric drop, maximum room for the number.
  const C_DROP =
    'M50 4 C64 30 92 50 92 78 C92 102 74 118 50 118 C26 118 8 102 8 78 C8 50 36 30 50 4 Z';

  const VARIANTS = {
    A: { label: 'Concentric', layers: [OUTER_A, OUTER_A, OUTER_A], scales: [1, 0.76, 0.56], origin: [50, 116], numY: 95, numSize: [36, 34, 26] },
    B: { label: 'Licks', layers: [B_OUT, B_MID, B_IN], scales: [1, 1, 1], origin: [50, 118], numY: 95, numSize: [36, 33, 25] },
    C: { label: 'Chunky drop', layers: [C_DROP, C_DROP, C_DROP], scales: [1, 0.76, 0.54], origin: [50, 118], numY: 90, numSize: [44, 40, 30] },
  };

  function numSize(v, n) {
    const d = String(n).length;
    return VARIANTS[v].numSize[Math.min(d, 3) - 1];
  }

  function flameSVG(v, n) {
    const V = VARIANTS[v];
    const lit = n > 0;
    const uid = 'f' + Math.random().toString(36).slice(2, 8);
    const colors = [C.red, C.orange, C.yellow];
    const [ox, oy] = V.origin;
    const layers = V.layers
      .map((d, i) => {
        const s = V.scales[i];
        const t = s === 1 ? '' : `translate(${ox} ${oy}) scale(${s}) translate(${-ox} ${-oy})`;
        let style;
        if (lit) style = `fill:${colors[i]}`;
        else style = i === 0 ? `fill:none;stroke:${C.grey};stroke-width:3.5` : 'display:none';
        return `<g transform="${t}"><path class="layer l${i}" d="${d}" style="${style}"/></g>`;
      })
      .join('');
    return `
<svg class="flame ${lit ? 'lit' : 'unlit'}" viewBox="0 -2 100 122" role="img" aria-label="Streak: ${n}">
  <defs>
    <clipPath id="${uid}c"><path d="${V.layers[0]}"/></clipPath>
    <linearGradient id="${uid}g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="white" stop-opacity="0"/>
      <stop offset="0.5" stop-color="oklch(0.95 0.05 230)" stop-opacity="0.85"/>
      <stop offset="1" stop-color="white" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <g class="body">${layers}</g>
  <g clip-path="url(#${uid}c)"><rect class="frost" x="-10" y="-70" width="120" height="70" fill="url(#${uid}g)"/></g>
  <text class="num" x="50" y="${V.numY}" text-anchor="middle" dominant-baseline="central"
    font-family="Fredoka, sans-serif" font-weight="700" font-size="${numSize(v, n)}"
    fill="${lit ? C.num : C.grey}">${n}</text>
</svg>`;
  }

  const SNOW =
    '<line x1="2" x2="22" y1="12" y2="12"/><line x1="12" x2="12" y1="2" y2="22"/><path d="m20 16-4-4 4-4"/><path d="m4 8 4 4-4 4"/><path d="m16 4-4 4-4-4"/><path d="m8 20 4-4 4 4"/>';

  function freezeIcon(style, on) {
    const cls = `fz ${on ? 'on' : 'off'}`;
    if (style === 'disc') {
      const disc = on
        ? `<circle cx="12" cy="12" r="14" fill="${C.iceBg}" stroke="${C.ice}" stroke-width="1.5"/>`
        : `<circle cx="12" cy="12" r="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 3"/>`;
      return `<svg class="${cls}" viewBox="-4 -4 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${disc}${on ? `<g>${SNOW}</g>` : ''}</svg>`;
    }
    if (style === 'cube') {
      return on
        ? `<svg class="${cls}" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="5" fill="${C.ice}"/><rect x="6" y="6" width="6" height="3" rx="1.5" fill="white" opacity=".7"/><rect x="6" y="11" width="2.5" height="2.5" rx="1" fill="white" opacity=".5"/></svg>`
        : `<svg class="${cls}" viewBox="0 0 24 24"><rect x="3.75" y="3.75" width="16.5" height="16.5" rx="4.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`;
    }
    return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${on ? 2.4 : 1.6}" stroke-linecap="round" stroke-linejoin="round">${SNOW}</svg>`;
  }

  const FREEZE_CAP = 7;

  // Every pending timer goes through later() so a new replay can cancel the old one.
  const timers = [];
  let epoch = 0;
  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
  function cancelAll() { timers.forEach(clearTimeout); timers.length = 0; epoch++; }

  function meterHTML(style, count) {
    let h = '';
    for (let i = 0; i < FREEZE_CAP; i++) h += `<span class="slot" data-i="${i}">${freezeIcon(style, i < count)}</span>`;
    return `<div class="meter" role="img" aria-label="Freezes: ${count} of ${FREEZE_CAP}">${h}</div>`;
  }

  function restart(el, cls) {
    el.classList.remove(cls);
    void el.getBoundingClientRect();
    el.classList.add(cls);
  }

  function countUp(svg, v, from, to, ms) {
    const t = svg.querySelector('.num');
    const t0 = performance.now();
    const myEpoch = epoch;
    function step(now) {
      if (myEpoch !== epoch) return;
      const p = Math.min(1, (now - t0) / ms);
      const n = Math.round(from + (to - from) * p);
      t.textContent = n;
      t.setAttribute('font-size', numSize(v, n));
      if (p < 1) requestAnimationFrame(step);
      else restart(t, 'bump');
    }
    requestAnimationFrame(step);
  }

  // Streak went up: flame grows from an ember, layers flicker, number ticks up.
  function ignite(host, v, from, to) {
    host.innerHTML = flameSVG(v, to);
    const svg = host.querySelector('svg');
    svg.querySelector('.num').textContent = from;
    restart(svg, 'ignite');
    later(() => countUp(svg, v, from, to, 500), 450);
  }

  // A freeze was used: slot cracks and falls apart, then frost sweeps the flame.
  function freezeUsed(meterHost, flameHost, style, from, to) {
    const slots = meterHost.querySelectorAll('.slot');
    let delay = 0;
    for (let i = from - 1; i >= to; i--) {
      const slot = slots[i];
      later(() => crack(slot, style), delay);
      delay += 550;
    }
    later(() => {
      const svg = flameHost.querySelector('svg');
      if (svg) restart(svg, 'frosted');
    }, delay + 100);
  }

  function crack(slot, style) {
    restart(slot, 'shake');
    later(() => {
      slot.classList.remove('shake');
      slot.innerHTML =
        freezeIcon(style, false) +
        `<span class="half left">${freezeIcon(style, true)}</span>` +
        `<span class="half right">${freezeIcon(style, true)}</span>`;
      later(() => slot.querySelectorAll('.half').forEach((h) => h.remove()), 700);
    }, 320);
  }

  // A freeze was earned: the new slot pops in with a ring.
  function freezeEarned(meterHost, style, to, delay = 0) {
    const slot = meterHost.querySelectorAll('.slot')[to - 1];
    if (!slot) return;
    later(() => {
      slot.innerHTML = freezeIcon(style, true);
      restart(slot, 'popin');
    }, delay);
  }

  window.Streak = { VARIANTS, FREEZE_CAP, flameSVG, freezeIcon, meterHTML, ignite, freezeUsed, freezeEarned, later, cancelAll };
})();
