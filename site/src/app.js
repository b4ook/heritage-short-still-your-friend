const FILM = window.FILM;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? (el.className = v) : el.setAttribute(k, v);
  for (const kid of kids.flat()) if (kid != null) el.append(kid);
  return el;
};
document.documentElement.classList.add("js");

/* ---------- Content (all from the repository's own evidence) ---------- */

const NAMES = { abebe: "Abebe", kassa: "Kassa", young_abebe: "Young Abebe", young_kassa: "Young Kassa" };
const EXPERIMENTS = [
  ["E1", "One loudness pass is enough", "rejected", "A single pass measured −15.22 LUFS. Two passes: −14.72, and −14.03 on the final film."],
  ["E2", "original_size makes subtitles pixel-sized", "rejected", "Text rendered wider than the frame. Setting PlayResX/PlayResY to the output size fixed it."],
  ["E3", "Prompt wording can undo posed framing", "rejected", "“Candid, not looking at the camera” changed nothing. The reference images set the framing."],
  ["E4", "Reference images on or off per shot", "adopted", "Off for wide and candid shots: all four now show the intended scene, and the men stay recognisable."],
  ["E5", "Descriptions fix ethnicity drift and props", "adopted", "Adding Habesha features and a round soccer ball fixed the portraits. Approved by the author."],
  ["E6", "Casting two elderly Amharic voices", "decided", "Gemini has one Amharic male voice. Five auditions; Kassa and Abebe each got one."],
  ["E7", "Flash and Flash-Lite sound alike", "accepted", "Judged close enough by the author. Every line records which model made it."],
  ["E8", "Delivery style changes line length", "adopted", "“Laughing softly” took 11.0 s; “warm, a little amused” 5.5 s for the same words."],
  ["E9", "Pacing absorbs length without cuts", "partly", "Shorter tails, wordless shots and end cards: 100.6 s → 95.3 s. E8 closed the rest."],
  ["E10", "Int8 quantization is safe on a T4", "rejected", "It produced NaN audio. Without it, all three tracks rendered in 14–18 s each."],
  ["E11", "Depth parallax moves stills better than zoompan", "adopted", "Version two: eased, sub-pixel moves over a depth map, with dissolves. 6.7 s of compute per 4 s of film."],
];
const FAILURES = [
  ["F1", "Gemini TTS rejected the old speech call", "Text-to-speech moved to the Interactions API, with style in a speech annotation."],
  ["F2", "Kaggle ran with no GPU", "The account needed phone verification. After it, a Tesla T4 in 32 s."],
  ["F3", "FFmpeg lacked subtitles and drawtext", "Installed ffmpeg-full; the pipeline prefers it without relinking the system build."],
  ["F4", "Subtitles rendered huge, off the frame", "SRT keeps a 288-line canvas. PlayRes set to the output size fixed it."],
  ["F5", "Narration hung for ten minutes, silently", "A stack dump showed the SDK retrying a 10-a-day quota error. Retries now surface every failure."],
  ["F6", "Flash-Lite had the same daily limit", "Its quota resets on a rolling window; the last lines arrived hours early."],
  ["F7", "ACE-Step needs Python 3.12, Kaggle runs 3.13", "The kernel builds the repo's own uv environment on 3.12."],
  ["F8", "Music came out as NaN on the T4", "Int8 quantization was the cause, not fp16. Removed."],
];
const ETHICS = [
  ["No real person", "Abebe and Kassa are fictional. Faces come from text descriptions; voices are stock Gemini voices. No reference photo of a real person was used."],
  ["Labelled as AI", "A closing card names every model that made something in this cut, and the platform AI label is switched on when posted."],
  ["Licences checked", "FLUX.2 klein 4B and Wan 2.2 are Apache 2.0. ACE-Step 1.5 is MIT, and its outputs may be used commercially."],
];

const pad = (n) => String(n).padStart(2, "0");
const tc = (sec) => `${pad(Math.floor(sec / 60))}:${pad(Math.floor(sec % 60))}`;

function renderShots() {
  // Each shot is one frame on a 35 mm strip. Edge print carries the shot number and where it starts in the cut.
  const track = $("[data-shots]");
  let at = 0;
  FILM.shots.forEach((shot, i) => {
    shot.start = at;
    at += shot.duration;
    track.append(h("li", { class: "frame" },
      h("span", { class: "edge edge-top", "aria-hidden": "true" }, `HERITAGE 5399  ▸ ${pad(i + 1)}A`),
      h("button", { class: "frame-pic", type: "button", "aria-label": `Shot ${i + 1}: ${shot.purpose}` },
        h("img", { src: shot.image, alt: "", loading: i < 4 ? "eager" : "lazy", decoding: "async" })),
      h("span", { class: "edge edge-bottom", "aria-hidden": "true" }, `${pad(i + 1)}  ${tc(shot.start)}`)));
  });
}

function gateBody(shot) {
  const lines = shot.lines.length
    ? h("ul", { class: "gate-lines" }, shot.lines.map((l) => h("li", {},
        h("span", { class: "who" }, NAMES[l.speaker] || l.speaker, l.reworded ? h("span", { class: "gate-new" }, "New wording") : null),
        h("span", { class: "am", lang: "am" }, l.text),
        h("span", { class: "en" }, l.en))))
    : h("p", { class: "gate-silent" }, "No dialogue. The picture carries it.");
  return [h("p", { class: "gate-purpose" }, shot.purpose), lines];
}

function renderCast() {
  const root = $("[data-cast]");
  for (const c of FILM.characters) {
    const desc = c.description.replace(/^[^:]+:\s*/, "").split(",").slice(0, 3).join(",");
    root.append(h("figure", { class: "person" },
      h("div", { class: "person-img" }, h("img", { src: c.image, alt: `Reference portrait of ${NAMES[c.id]}`, loading: "lazy" })),
      h("figcaption", {},
        h("div", { class: "person-name" }, NAMES[c.id] || c.id),
        h("div", { class: "person-desc" }, desc),
        c.voice ? h("span", { class: "person-voice" }, `Voice · ${c.voice}`) : null,
        h("div", { class: "person-lines", "data-person-lines": c.id }),
        h("p", { class: "person-quote", "data-person-quote": c.id }))));
  }
}

function renderEvidence() {
  $("[data-experiments]").append(...EXPERIMENTS.map(([id, title, kind, result]) => h("article", { class: "card" },
    h("div", { class: "card-top" }, h("span", { class: "card-id" }, id), h("span", { class: "chip", "data-kind": kind }, kind)),
    h("h3", {}, title), h("p", { class: "result" }, result))));
  $("[data-failures]").append(...FAILURES.map(([id, title, fix]) => h("article", { class: "card" },
    h("div", { class: "card-top" }, h("span", { class: "card-id" }, id), h("span", { class: "chip", "data-kind": "fixed" }, "fixed")),
    h("h3", {}, title), h("p", {}, fix))));
  $("[data-ethics]").append(...ETHICS.map(([t, p]) => h("div", { class: "ethics-item" }, h("h3", {}, t), h("p", {}, p))));
}

function renderClosing() {
  const [first, ...rest] = FILM.endCards;
  $("[data-closing]").replaceChildren(

    h("p", { class: "closing-am", lang: "am", "data-reveal": "" }, first.text),
    h("p", { class: "closing-en", "data-reveal": "" }, first.en),
    h("div", { class: "closing-rest" }, rest.map((c) => h("div", { "data-reveal": "" },
      h("p", { class: "am", lang: "am" }, c.text), h("p", { class: "en" }, c.en)))));
}

/* ---------- SVG helpers ---------- */

const SVGNS = "http://www.w3.org/2000/svg";
const svgEl = (tag, attrs) => {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

/* ---------- Bento ---------- */

function renderBento() {
  // The voice waveform sits exactly where the score dips (x 80 to 254), so the cause is visible.
  const voice = $(".duck-voice");
  const rand = seeded(5);
  for (let x = 80; x < 254; x += 5) {
    const hgt = 6 + Math.abs(Math.sin(x / 9)) * 22 + rand() * 10;
    voice.append(svgEl("rect", { x, y: 46 - hgt / 2, width: 3, height: hgt, rx: 1.5 }));
  }
  const shots = [...FILM.shots, ...FILM.shots].slice(0, 15);
  $("[data-frames]").append(...shots.map((s) => h("img", { src: s.image, alt: "", loading: "lazy", decoding: "async" })));

  const typed = $("[data-type]");
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const tile = e.target;
      io.unobserve(tile);
      if (tile.dataset.tile === "flow") {
        const items = $$(".flow li", tile);
        const first = items[0], last = items.at(-1);
        const span = last.offsetTop + last.offsetHeight / 2 - (first.offsetTop + first.offsetHeight / 2);
        $(".flow", tile).style.setProperty("--flow-h", `${span}px`);
      }
      if (tile.dataset.tile === "editor" && !reduced) {
        const full = typed.textContent;
        typed.textContent = "";
        [...full].forEach((ch, i) => setTimeout(() => { typed.textContent += ch; }, 700 + i * 75));
      }
      setTimeout(() => tile.classList.add("play"), 150);
    }
  }, { threshold: 0.45 });
  $$("[data-tile]").forEach((t) => io.observe(t));
}

/* ---------- Entrances ---------- */

function splitTitle() {
  const el = $("[data-split]");
  const words = el.textContent.split(" ");
  el.textContent = "";
  words.forEach((w, i) => el.append(h("span", { class: "word" }, w + (i < words.length - 1 ? " " : ""))));
}

function heroEntrance() {
  // Non-uniform stagger: nav first, then the title word by word, then the supporting lines, then the film.
  const seq = [[$(".nav"), 0], ...$$(".display .word").map((w, i) => [w, 140 + i * 70 + i * i * 8]),
    [$(".hero .eyebrow"), 80], [$(".hero-am"), 520], [$(".lede"), 620], [$(".hero-actions"), 720]];
  for (const [el, delay] of seq) setTimeout(() => el.classList.add("is-in"), reduced ? 0 : delay);
  setTimeout(() => $("[data-reveal-card]").classList.add("is-in"), reduced ? 0 : 820);
}

function observeReveals() {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const group = e.target.parentElement;
      const siblings = [...group.children].filter((c) => !c.classList.contains("is-in"));
      const index = Math.max(0, siblings.indexOf(e.target));
      setTimeout(() => e.target.classList.add("is-in"), reduced ? 0 : Math.min(index, 6) * 60);
      io.unobserve(e.target);
    }
  }, { rootMargin: "0px 0px -10% 0px", threshold: 0.1 });
  $$("[data-reveal], .person, .tile, .card, .ethics-item").forEach((el) => io.observe(el));
}

/* ---------- Small interactions ---------- */

function reel() {
  // The frame nearest the strip's centre is "in the gate": lit, and its words shown below.
  const strip = $("[data-rail]");
  const frames = $$(".frame", strip);
  const body = $("[data-gate]");
  let current = -1;
  const center = (el) => el.offsetLeft + el.offsetWidth / 2 - strip.clientWidth / 2;
  const go = (i) => strip.scrollTo({ left: center(frames[Math.max(0, Math.min(frames.length - 1, i))]), behavior: reduced ? "auto" : "smooth" });
  const show = (i, force = false) => {
    if (i === current && !force) return;
    const dir = i > current ? 1 : -1;
    current = i;
    frames.forEach((f, k) => f.classList.toggle("is-gate", k === i));
    const shot = FILM.shots[i];
    $("[data-gate-n]").textContent = pad(i + 1);
    $("[data-gate-tag]").textContent = `${shot.size} · ${shot.duration.toFixed(1)} s · from ${tc(shot.start)} · ${shot.move || ""}`;
    body.replaceChildren(...gateBody(shot));
    if (!reduced) {
      body.animate([{ opacity: 0, transform: `translateX(${dir * 14}px)`, filter: "blur(4px)" }, { opacity: 1, transform: "none", filter: "none" }],
        { duration: 320, easing: "cubic-bezier(0.23, 1, 0.32, 1)" });
    }
  };
  let ticking = false;
  strip.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      const mid = strip.scrollLeft + strip.clientWidth / 2;
      let best = 0, dist = Infinity;
      frames.forEach((f, k) => { const d = Math.abs(f.offsetLeft + f.offsetWidth / 2 - mid); if (d < dist) { dist = d; best = k; } });
      show(best);
    });
  }, { passive: true });
  frames.forEach((f, k) => $(".frame-pic", f).addEventListener("click", () => go(k)));
  $("[data-rail-prev]").addEventListener("click", () => go(current - 1));
  $("[data-rail-next]").addEventListener("click", () => go(current + 1));
  strip.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); go(current - 1); }
    if (e.key === "ArrowRight") { e.preventDefault(); go(current + 1); }
  });
  show(0);
  refreshGate = () => show(current, true);
}

let refreshGate = () => {};

function tabs() {
  const buttons = $$("[data-tab]");
  const pill = $(".tabs-pill", buttons[0].parentElement);
  const place = (btn) => {
    pill.style.width = `${btn.offsetWidth}px`;
    pill.style.transform = `translateX(${btn.offsetLeft}px)`;
  };
  const select = (btn) => {
    for (const b of buttons) {
      const on = b === btn;
      b.setAttribute("aria-selected", on);
      $(`#${b.getAttribute("aria-controls")}`).hidden = !on;
    }
    place(btn);
    $$(".card", $(`#${btn.getAttribute("aria-controls")}`)).forEach((c) => c.classList.add("is-in"));
  };
  buttons.forEach((b) => b.addEventListener("click", () => select(b)));
  requestAnimationFrame(() => place(buttons[0]));
  addEventListener("resize", () => place(buttons.find((b) => b.getAttribute("aria-selected") === "true")));
}

/* ---------- Immersive theatre ---------- */

const theatre = $("[data-theatre]");
const frame = $("[data-frame]");
const video = $("[data-video]");
const ambient = $("[data-ambient]");
const ctx = ambient.getContext("2d", { alpha: false });
let ratio = matchMedia("(orientation: portrait)").matches ? "9x16" : "16x9";
let idleTimer = 0;
let ambientTimer = 0;
let opener = null;

function targetRect(r = ratio) {
  const aspect = r === "16x9" ? 16 / 9 : 9 / 16;
  const maxW = innerWidth * (innerWidth < 720 ? 0.94 : 0.86);
  const maxH = innerHeight * (innerWidth < 720 ? 0.8 : 0.82);
  let w = maxW, hgt = w / aspect;
  if (hgt > maxH) { hgt = maxH; w = hgt * aspect; }
  return { left: (innerWidth - w) / 2, top: (innerHeight - hgt) / 2 - (innerWidth < 720 ? 24 : 18), width: w, height: hgt };
}

function placeFrame(rect) {
  Object.assign(frame.style, { left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px` });
}

function flipFrom(from, to, duration, easing) {
  const dx = from.left - to.left, dy = from.top - to.top;
  const sx = from.width / to.width, sy = from.height / to.height;
  frame.style.transformOrigin = "0 0";
  return frame.animate([
    { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`, borderRadius: "36px" },
    { transform: "none", borderRadius: "28px" },
  ], { duration, easing, fill: "both" });
}

function drawAmbient() {
  if (video.readyState >= 2) ctx.drawImage(video, 0, 0, ambient.width, ambient.height);
}

function placePill(tabsEl) {
  const on = $('[aria-selected="true"]', tabsEl);
  const pill = $(".tabs-pill", tabsEl);
  pill.style.width = `${on.offsetWidth}px`;
  pill.style.transform = `translateX(${on.offsetLeft}px)`;
}

function setRatio(r, animate = true) {
  // One ratio for the card and the theatre: the card morphs to the new shape, the poster refocuses.
  const card = $("[data-reveal-card]");
  const hit = $(".film-card-hit");
  const poster = $(".film-poster");
  const from = hit.getBoundingClientRect();
  ratio = r;
  card.dataset.ratio = r;
  poster.src = FILM.posters[r];
  const tabsEl = $(".ratio-tabs");
  $$("[data-ratio-tab]", tabsEl).forEach((b) => b.setAttribute("aria-selected", b.dataset.ratioTab === r));
  placePill(tabsEl);
  if (!animate || reduced) return;
  const to = hit.getBoundingClientRect();
  hit.animate([{ width: `${from.width}px`, height: `${from.height}px` }, { width: `${to.width}px`, height: `${to.height}px` }],
    { duration: 560, easing: "cubic-bezier(0.77, 0, 0.175, 1)" });
  poster.animate([{ opacity: 0.2, filter: "blur(10px)" }, { opacity: 1, filter: "none" }], { duration: 520, easing: "ease" });
}

let version = 1;

// "How it was made" per version. Counts come from the build (V.newLines); the rest describes the pipeline.
const MAKING = {
  1: (V) => ({
    edCopy: "<strong>Edit one line.</strong> Only that line is made again.",
    edFile: "storyboard.json", edSpeaker: '"abebe"', edText: '"አሁንም ነኝ።"', edTyped: "I still am.",
    log: [["s11.3", "cache_hit"], ["s12.0", "cache_hit"], ["s12.1", "ok · 1 call"]],
    statCopy: "<strong>Rebuilds from cache.</strong> Every keyframe and line already exists.",
    statLead: "Model calls to rebuild", statNum: "0", statFoot: "28 keyframes · 16 lines · 3 scores",
    motion: "Ken Burns · FFmpeg", assembly: "FFmpeg · cuts",
    framesCopy: "<strong>24 keyframes.</strong> Framed natively for both screens.",
  }),
  2: (V) => ({
    edCopy: "<strong>Reword a line.</strong> Only reworded lines are voiced again.",
    edFile: "storyboard_v2.json", edSpeaker: '"kassa"', edText: '"ይቅርታ... ማን ልበል?"', edTyped: "Sorry... who are you?",
    log: [["s11.0", "cache_hit"], ["s12.1", "cache_hit"], ["s03.0", "ok · 1 call"]],
    statCopy: "<strong>Version two reused the cache.</strong> Same keyframes, same score.",
    statLead: "New model calls for version two", statNum: String(V.newLines),
    statFoot: `${V.newLines} voice lines · 0 images · 0 scores`,
    motion: "Depth Anything V2", assembly: "FFmpeg · dissolves",
    framesCopy: "<strong>The same 24 keyframes.</strong> Moved with depth parallax.",
  }),
};

function applyVersionSections(V) {
  const m = MAKING[V.id](V);
  $$("[data-v]").forEach((el) => { el.textContent = m[el.dataset.v]; });
  $$("[data-vhtml]").forEach((el) => { el.innerHTML = m[el.dataset.vhtml]; });
  $("[data-type]").textContent = m.edTyped;
  $("[data-log]").replaceChildren(...m.log.map(([id, status], i) => h("div",
    { class: i === m.log.length - 1 ? "log-row log-new" : "log-row" },
    h("span", { class: i === m.log.length - 1 ? "dot dot-live" : "dot" }), id,
    h("em", { class: status.startsWith("ok") ? "ok" : "" }, status))));
  $$("[data-version-chip]").forEach((el) => { el.textContent = FILM.versions.length > 1 ? V.label : ""; });
  FILM.shots.forEach((s, i) => Object.assign(s, { start: V.shots[i].start, duration: V.shots[i].length, move: V.shots[i].move }));
  $$(".edge-bottom").forEach((el, i) => { el.textContent = `${pad(i + 1)}  ${tc(V.shots[i].start)}`; });
  for (const c of FILM.characters) {
    const info = V.cast[c.id];
    $(`[data-person-lines="${c.id}"]`).textContent = !info.lines ? "No lines · seen in the opening photo"
      : `${info.lines} lines` + (V.id > 1 ? ` · ${info.reworded} reworded` : "");
    $(`[data-person-quote="${c.id}"]`).replaceChildren(...(info.sample
      ? [h("span", { class: "am", lang: "am" }, info.sample.text), h("span", { class: "en" }, info.sample.en)] : []));
    $(`[data-person-quote="${c.id}"]`).hidden = !info.sample;
  }
}

function setVersion(n, animate = true) {
  // A version swaps the films, posters, dialogue and end cards; the pictures are the same keyframes.
  const V = FILM.versions.find((v) => v.id === n) || FILM.versions[0];
  version = V.id;
  FILM.films = V.films;
  FILM.posters = V.posters;
  FILM.shots.forEach((s, i) => { s.lines = V.lines[i]; });
  FILM.endCards = V.endCards;
  applyVersionSections(V);
  const tabsEl = $("[data-version-tabs]");
  $$("[data-version-tab]", tabsEl).forEach((b) => b.setAttribute("aria-selected", Number(b.dataset.versionTab) === version));
  placePill(tabsEl);
  $("[data-version-note]").textContent = V.note;
  const poster = $(".film-poster");
  poster.src = V.posters[ratio];
  if (animate && !reduced) {
    poster.animate([{ opacity: 0.3, filter: "blur(8px)" }, { opacity: 1, filter: "none" }], { duration: 420, easing: "ease" });
  }
  refreshGate();
  renderClosing();
  if (animate) $$("[data-closing] [data-reveal]").forEach((el) => el.classList.add("is-in"));
  const url = new URL(location.href);
  if (version === 1) url.searchParams.delete("version"); else url.searchParams.set("version", version);
  history.replaceState(null, "", url);
}

function versionSwitch() {
  const tabsEl = $("[data-version-tabs]");
  const pill = $(".tabs-pill", tabsEl);
  for (const v of FILM.versions) {
    const b = h("button", { role: "tab", "aria-selected": "false", "data-version-tab": v.id }, v.label);
    b.addEventListener("click", () => { if (v.id !== version) setVersion(v.id); });
    tabsEl.insertBefore(b, pill);
  }
  if (FILM.versions.length < 2) tabsEl.hidden = true;
  const asked = Number(new URLSearchParams(location.search).get("version"));
  setVersion(FILM.versions.some((v) => v.id === asked) ? asked : 1, false);
  document.fonts.ready.then(() => placePill(tabsEl));
  addEventListener("resize", () => placePill(tabsEl));
}

function ratioSwitch() {
  const tabsEl = $(".ratio-tabs");
  $$("[data-ratio-tab]", tabsEl).forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.ratioTab !== ratio) setRatio(b.dataset.ratioTab);
  }));
  setRatio(ratio, false);
  document.fonts.ready.then(() => placePill(tabsEl));
  addEventListener("resize", () => placePill(tabsEl));
}

function setSource(r, keepTime) {
  const t = keepTime ? video.currentTime : 0;
  const wasPlaying = !video.paused;
  video.src = FILM.films[r];
  video.poster = FILM.posters[r];
  $("[data-toggle-ratio]").textContent = r === "16x9" ? "9:16" : "16:9";
  if (keepTime) {
    video.addEventListener("loadedmetadata", () => { video.currentTime = t; if (wasPlaying) video.play(); }, { once: true });
  }
}

function wake() {
  theatre.classList.remove("is-idle");
  clearTimeout(idleTimer);
  if (!video.paused) idleTimer = setTimeout(() => theatre.classList.add("is-idle"), 2400);
}

function openTheatre(event) {
  opener = event.currentTarget;
  const poster = $(".film-poster");
  const from = poster.getBoundingClientRect();
  setSource(ratio, false);
  video.muted = false;
  const playing = video.play(); // inside the click, so sound is allowed
  playing?.catch(() => {});

  theatre.hidden = false;
  document.body.style.overflow = "hidden";
  ambient.width = 48; ambient.height = 27;
  const to = targetRect();
  placeFrame(to);
  requestAnimationFrame(() => theatre.classList.add("is-open"));

  if (reduced) {
    theatre.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 250, easing: "ease" });
  } else {
    theatre.animate([{ backgroundColor: "rgba(5,6,7,0)" }, { backgroundColor: "rgba(5,6,7,1)" }],
      { duration: 650, easing: "cubic-bezier(0.23, 1, 0.32, 1)" });
    flipFrom(from, to, 900, "cubic-bezier(0.32, 0.72, 0, 1)");
    $("[data-controls]").animate([{ opacity: 0, transform: "translateY(16px)", filter: "blur(6px)" }, { opacity: 1, transform: "none", filter: "none" }],
      { duration: 600, delay: 450, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" });
  }
  clearInterval(ambientTimer);
  ambientTimer = setInterval(drawAmbient, 120);
  $("[data-toggle-play]").focus({ preventScroll: true });
  wake();
}

async function closeTheatre() {
  if (theatre.hidden) return;
  video.pause();
  clearInterval(ambientTimer);
  theatre.classList.remove("is-open", "is-idle");
  const to = $(".film-poster").getBoundingClientRect();
  if (!reduced) {
    const from = frame.getBoundingClientRect();
    const dx = to.left - from.left, dy = to.top - from.top;
    const out = frame.animate([
      { transform: "none", borderRadius: "28px" },
      { transform: `translate(${dx}px, ${dy}px) scale(${to.width / from.width}, ${to.height / from.height})`, borderRadius: "36px" },
    ], { duration: 520, easing: "cubic-bezier(0.32, 0.72, 0, 1)", fill: "forwards" });
    theatre.animate([{ backgroundColor: "rgba(5,6,7,1)" }, { backgroundColor: "rgba(5,6,7,0)" }], { duration: 480, easing: "ease", fill: "forwards" });
    $("[data-controls]").animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: "forwards" });
    await out.finished.catch(() => {});
  }
  frame.getAnimations().forEach((a) => a.cancel());
  theatre.getAnimations().forEach((a) => a.cancel());
  $("[data-controls]").getAnimations().forEach((a) => a.cancel());
  theatre.hidden = true;
  document.body.style.overflow = "";
  opener?.focus({ preventScroll: true });
}

function fmt(s) {
  if (!isFinite(s)) return "0:00";
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

function theatreControls() {
  const scrub = $("[data-scrub]");
  const playBtn = $("[data-toggle-play]");
  const playIcon = $("[data-icon-play]");
  const syncPlay = () => {
    const playing = !video.paused;
    playBtn.setAttribute("aria-label", playing ? "Pause" : "Play");
    playIcon.innerHTML = playing ? '<path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/>' : '<path d="M8 5.5v13l10.5-6.5z"/>';
    wake();
  };
  $$("[data-open-film]").forEach((b) => b.addEventListener("click", openTheatre));
  playBtn.addEventListener("click", () => (video.paused ? video.play() : video.pause()));
  video.addEventListener("click", () => (video.paused ? video.play() : video.pause()));
  video.addEventListener("play", syncPlay);
  video.addEventListener("pause", syncPlay);
  video.addEventListener("ended", () => { syncPlay(); theatre.classList.remove("is-idle"); });
  video.addEventListener("loadedmetadata", () => { $("[data-duration]").textContent = fmt(video.duration); });
  video.addEventListener("timeupdate", () => {
    const p = video.duration ? video.currentTime / video.duration : 0;
    scrub.value = Math.round(p * 1000);
    scrub.style.setProperty("--p", `${p * 100}%`);
    $("[data-time]").textContent = fmt(video.currentTime);
  });
  scrub.addEventListener("input", () => {
    if (video.duration) video.currentTime = (scrub.value / 1000) * video.duration;
    scrub.style.setProperty("--p", `${scrub.value / 10}%`);
  });
  $("[data-toggle-mute]").addEventListener("click", (e) => {
    video.muted = !video.muted;
    e.currentTarget.setAttribute("aria-label", video.muted ? "Unmute" : "Mute");
    e.currentTarget.style.opacity = video.muted ? 0.55 : 1;
  });
  $("[data-toggle-ratio]").addEventListener("click", () => {
    const from = frame.getBoundingClientRect();
    setRatio(ratio === "16x9" ? "9x16" : "16x9", false);
    setSource(ratio, true);
    const to = targetRect();
    placeFrame(to);
    if (!reduced) flipFrom(from, to, 650, "cubic-bezier(0.77, 0, 0.175, 1)");
  });
  $("[data-close]").addEventListener("click", closeTheatre);
  theatre.addEventListener("pointermove", wake);
  theatre.addEventListener("touchstart", wake, { passive: true });
  addEventListener("keydown", (e) => {
    if (theatre.hidden) return;
    if (e.key === "Escape") closeTheatre();
    else if (e.key === " " && e.target === document.body) { e.preventDefault(); video.paused ? video.play() : video.pause(); }
    else if (e.key.toLowerCase() === "m") $("[data-toggle-mute]").click();
    wake();
  });
  addEventListener("resize", () => { if (!theatre.hidden) placeFrame(targetRect()); });
  document.addEventListener("visibilitychange", () => { if (document.hidden && !theatre.hidden) video.pause(); });
}

/* ---------- Boot ---------- */
splitTitle();
renderShots();
renderCast();
renderBento();
renderEvidence();
renderClosing();
reel();
versionSwitch();
ratioSwitch();
tabs();
theatreControls();
observeReveals();
document.fonts.ready.then(heroEntrance);
setTimeout(heroEntrance, 1200); // fonts slow or blocked: show the page anyway
