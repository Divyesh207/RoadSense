// @ts-nocheck
/* eslint-disable */
/*
 * Landing hero scene: an Indian urban road in daylight, with traffic and potholes (three.js r128).
 * Geometry is generated here. Two CC0 Poly Haven assets are loaded from `ASSETS` (scanned asphalt
 * and a photographed sky, see public/road-scene/CREDITS.md); the scene still renders without them.
 * It is a demonstration: nothing in it comes from the platform's data.
 *
 * Browser only. createRoadScene() throws when WebGL is unavailable; the caller shows the poster.
 */
import * as THREE from 'three';
import { Sky } from 'three/examples/jsm/objects/Sky.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { BufferGeometryUtils } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export function createRoadScene(host, ASSETS) {
  let disposed = false;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ------------------------------------------------------------------ helpers
  let seed = 11;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const range = (a, b) => a + (b - a) * rnd();
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const h2 = (x, y) => { const n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return n - Math.floor(n); };
  function vnoise(x, y, py) { // smooth value noise; py makes it repeat along y
    const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
    const w = (v) => (py ? ((v % py) + py) % py : v);
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    return lerp(lerp(h2(xi, w(yi)), h2(xi + 1, w(yi)), sx), lerp(h2(xi, w(yi + 1)), h2(xi + 1, w(yi + 1)), sx), sy);
  }
  const fbm = (x, y, py) => vnoise(x, y, py) * 0.55 + vnoise(x * 2.1, y * 2.1, py && py * 2.1) * 0.3 + vnoise(x * 4.3, y * 4.3, py && py * 4.3) * 0.15;
  const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; };

  // ------------------------------------------------------------------ renderer, sky, light
  const LOW = Math.min(innerWidth, innerHeight) < 700; // phones: lighter settings
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, LOW ? 1.5 : 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.5;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = LOW ? THREE.BasicShadowMap : THREE.PCFShadowMap; // soft filtering costs far more per pixel
  host.appendChild(renderer.domElement);
  const MAX_ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (c, repeat) => {
    const t = new THREE.CanvasTexture(c); t.anisotropy = MAX_ANISO;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
    return t;
  };
  const colorTex = (c, repeat) => { const t = tex(c, repeat); t.encoding = THREE.sRGBEncoding; return t; };
  const V3 = THREE.Vector3;

  // Everything on the ground lives in `world`, which is turned so the photographed sun sits behind-left of the camera.
  const scene = new THREE.Scene(), world = new THREE.Group(); scene.add(world);
  const HAZE = new THREE.Color(0xbfc9cf);
  scene.fog = new THREE.Fog(HAZE, 80, 310); scene.background = HAZE;
  const camera = new THREE.PerspectiveCamera(44, 1, 0.5, 2000);
  const CAM = { x: -5.6, y: 12.5, back: 10, lookX: -1.6, ahead: 36 };
  const LOCAL_SUN = new V3(-0.5, 0.68, 0.55).normalize(), sunDir = LOCAL_SUN.clone();
  const uInvWorld = { value: new THREE.Matrix4() }, holeUniform = { value: null };

  const reflective = []; let envTex = null;
  const shiny = (m) => { reflective.push(m); m.envMap = envTex; m.userData.env = m.envMapIntensity; return m; };
  function setEnv(t) { if (envTex) envTex.dispose(); envTex = t; for (const m of reflective) { m.envMap = t; m.needsUpdate = true; } }
  let sky = null;
  { // analytic sky: used until the photographed sky has loaded, and if it fails to load
    sky = new Sky(); sky.scale.setScalar(1500);
    const u = sky.material.uniforms;
    u.turbidity.value = 3.2; u.rayleigh.value = 1.1; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.8; u.sunPosition.value.copy(sunDir);
    scene.add(sky);
    const pm = new THREE.PMREMGenerator(renderer), s2 = new THREE.Scene(); s2.add(sky.clone());
    setEnv(pm.fromScene(s2).texture); pm.dispose();
  }
  const hemi = new THREE.HemisphereLight(0xcfe0f2, 0x6a665c, 1.15); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff2e0, 3.9);
  sun.castShadow = true; sun.shadow.mapSize.setScalar(LOW ? 2048 : 4096);
  Object.assign(sun.shadow.camera, { left: -60, right: 60, top: 80, bottom: -62, near: 1, far: 320 });
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03; sun.shadow.radius = 1.5;
  scene.add(sun, sun.target);

  function useSkyPhoto(t) {
    if (disposed) { t.dispose(); return; }
    const d = t.image.data, W = t.image.width, H = t.image.height; let best = 0, at = 0;
    for (let i = 0; i < W * H; i++) { const l = (d[i * 4] + d[i * 4 + 1] + d[i * 4 + 2]) * Math.pow(2, d[i * 4 + 3] - 136); if (l > best) { best = l; at = i; } }
    const lon = (((at % W) + 0.5) / W - 0.5) * 2 * Math.PI, lat = (0.5 - (Math.floor(at / W) + 0.5) / H) * Math.PI;
    sunDir.set(Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon));
    world.rotation.y = Math.atan2(sunDir.x, sunDir.z) - Math.atan2(LOCAL_SUN.x, LOCAL_SUN.z);
    world.updateMatrixWorld(true); uInvWorld.value.copy(world.matrixWorld).invert();
    // haze takes the colour of the photographed horizon
    const row = Math.floor(H * 0.492) * W; let r = 0, g = 0, b = 0;
    for (let x = 0; x < W; x += 4) { const i = (row + x) * 4, e = Math.pow(2, d[i + 3] - 136); r += d[i] * e; g += d[i + 1] * e; b += d[i + 2] * e; }
    const n = W / 4; HAZE.setRGB(r / n, g / n, b / n);
    const pm = new THREE.PMREMGenerator(renderer); setEnv(pm.fromEquirectangular(t).texture); pm.dispose();
    t.mapping = THREE.EquirectangularReflectionMapping; scene.background = t; if (sky) sky.visible = false;
    renderer.toneMappingExposure = 0.6; update(time);
  }
  new RGBELoader().load(ASSETS + 'kloofendal_43d_clear_puresky_1k.hdr', useSkyPhoto, undefined, () => {});

  // ------------------------------------------------------------------ road (metres). Traffic keeps left; the camera looks along -z.
  const LANE = 3.5, MEDIAN = 1.4, EDGE = 0.45, HALF = MEDIAN / 2 + EDGE + LANE * 2 + EDGE, CARRIAGE = HALF * 2, FOOT = 2.8;
  const LANES_X = [-(MEDIAN / 2 + EDGE + LANE * 1.5), -(MEDIAN / 2 + EDGE + LANE * 0.5), MEDIAN / 2 + EDGE + LANE * 0.5, MEDIAN / 2 + EDGE + LANE * 1.5];
  const ROAD_LEN = 460, MACRO_LEN = 160, WINDOW = 320, BEHIND = 30, TILE = 2.4;
  const decal = (extra) => Object.assign({ transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }, extra);

  // Materials that need the position on the road: pothole openings and kerb stripes
  function onRoad(material, code) {
    material.onBeforeCompile = (sh) => {
      sh.uniforms.uInvWorld = uInvWorld; sh.uniforms.holeMap = holeUniform;
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nuniform mat4 uInvWorld;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (uInvWorld * modelMatrix * vec4(position, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nuniform sampler2D holeMap;').replace('#include <map_fragment>', '#include <map_fragment>\n' + code);
    };
    return material;
  }
  const HOLE = `if (texture2D(holeMap, vec2((vWPos.x + ${HALF.toFixed(3)}) / ${CARRIAGE.toFixed(3)}, fract(-vWPos.z / ${WINDOW}.0))).r > 0.5) discard;`;
  const STRIPE = 'diffuseColor.rgb = mix(vec3(0.03), vec3(0.78, 0.6, 0.06), step(0.5, fract(vWPos.z / 2.4)));';
  const twoSided = (m) => { m.onBeforeCompile = (sh) => { sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_begin>', THREE.ShaderChunk.normal_fragment_begin.replace('gl_FrontFacing ? 1.0 : - 1.0', '1.0')); }; return m; };

  function speckle(S, base, spread, tint) { // a simple grainy tile
    const [c, g] = canvas(S, S), img = g.createImageData(S, S);
    for (let i = 0; i < S * S; i++) { const v = base + (Math.random() - 0.5) * spread; img.data.set([v + tint[0], v + tint[1], v + tint[2], 255], i * 4); }
    g.putImageData(img, 0, 0); return c;
  }
  const flat = (css) => { const [c, g] = canvas(4, 4); g.fillStyle = css; g.fillRect(0, 0, 4, 4); return c; };

  // Asphalt: scanned Poly Haven "Asphalt 02" once loaded; a plain grain until then (and if loading fails)
  const asphaltRep = [CARRIAGE / TILE, ROAD_LEN / TILE];
  const asphalt = new THREE.MeshStandardMaterial({ map: colorTex(speckle(256, 72, 34, [3, 2, 0]), asphaltRep), normalMap: tex(flat('rgb(128,128,255)'), asphaltRep), roughnessMap: tex(flat('#eee'), asphaltRep), roughness: 1, metalness: 0, envMapIntensity: 0.6 });
  asphalt.color.setScalar(1.12); // the scan is of dark, fresh asphalt; a worn city road is lighter
  for (const [file, key] of [['asphalt_02_diff_1k.jpg', 'map'], ['asphalt_02_nor_gl_1k.jpg', 'normalMap'], ['asphalt_02_arm_1k.jpg', 'roughnessMap']])
    new THREE.ImageLoader().load(ASSETS + file, (im) => { if (disposed) return; asphalt[key].image = im; asphalt[key].needsUpdate = true; if (!raf) update(time); });

  // Large-scale variation laid over the grain: brightness drift, tyre wear, oil, patches, cracks.
  function macroTexture() {
    const W = 512, H = 4096, [c, g] = canvas(W, H), px = W / CARRIAGE, py = H / MACRO_LEN, img = g.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const n = fbm(x / 70, y / 230, H / 230) - 0.5, fine = fbm(x / 9, y / 14, H / 14) - 0.5, xm = x / px - HALF;
      let dark = n * 0.5 + fine * 0.26 + (vnoise(x / 2.5, y / 2.5, H / 2.5) - 0.5) * 0.12;
      for (const lane of LANES_X) {
        for (const wheel of [-0.8, 0.8]) { const d = Math.abs(xm - lane - wheel); if (d < 0.42) dark += (1 - d / 0.42) * 0.13 * (0.6 + vnoise(x / 30, y / 400, H / 400) * 0.8); }
        const dc = Math.abs(xm - lane); if (dc < 0.3) dark += (1 - dc / 0.3) * 0.1 * vnoise(x / 20, y / 150, H / 150);
      }
      const edge = HALF - Math.abs(xm); if (edge < 0.7) dark -= (1 - edge / 0.7) * 0.22; // dust washed to the kerb
      const a = clamp(Math.abs(dark), 0, 0.5), v = dark > 0 ? 12 : 196;
      img.data.set([v, v, v - (dark > 0 ? 0 : 14), a * 255], (y * W + x) * 4);
    }
    g.putImageData(img, 0, 0);
    for (let i = 0; i < 5; i++) { // repaired patches
      const w = range(1.2, 3.4) * px, h = range(2, 9) * py, x = range(0.5 * px, W - w - 0.5 * px), y = range(50, H - h - 50);
      g.fillStyle = `rgba(22,22,24,${range(0.28, 0.5).toFixed(2)})`; g.fillRect(x, y, w, h);
      g.strokeStyle = 'rgba(8,8,9,0.45)'; g.lineWidth = 1.6; g.strokeRect(x, y, w, h);
    }
    const crack = (x, y, len, along, sealed) => {
      g.strokeStyle = sealed ? 'rgba(6,6,7,0.8)' : 'rgba(14,14,15,0.55)'; g.lineWidth = sealed ? 1.6 : 0.9; g.lineJoin = 'round';
      g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < len; k++) { if (along) { y += 9 + rnd() * 9; x += (rnd() - 0.5) * 7; } else { x += 7 + rnd() * 7; y += (rnd() - 0.5) * 9; } g.lineTo(x, y); }
      g.stroke();
    };
    for (let i = 0; i < 14; i++) crack(range(10, W - 10), range(40, H - 600), 14 + (rnd() * 26 | 0), true, rnd() < 0.15);
    for (let i = 0; i < 5; i++) crack(range(0, W * 0.6), range(40, H - 40), 8 + (rnd() * 14 | 0), false, false);
    return colorTex(c, [1, ROAD_LEN / MACRO_LEN]);
  }
  function paintTexture(dashed) { // worn road paint; the dashed tile is 3 m on, 6 m off
    const W = 64, H = 1024, [c, g] = canvas(W, H), img = g.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      let a = 1;
      if (dashed) { const m = (y / H) * 9; a = m > 0.5 && m < 3.5 ? clamp(Math.min(m - 0.5, 3.5 - m) * 14, 0, 1) : 0; }
      a *= clamp(Math.min(x, W - 1 - x) / 5 + vnoise(x / 3, y / 6, H / 6) * 0.8, 0, 1);
      const wear = fbm(x / 14, y / 40, H / 40); if (wear < 0.36) a *= clamp((wear - 0.2) / 0.16, 0.12, 1);
      if (Math.random() < 0.07) a *= 0.5;
      const v = 200 + Math.random() * 22; img.data.set([v, v, v - 6, a * 235], (y * W + x) * 4);
    }
    g.putImageData(img, 0, 0); return colorTex(c, [1, ROAD_LEN / (dashed ? 9 : 14)]);
  }

  const anchored = [], followers = []; // meshes that travel with the camera, and their textures that must stay fixed to the ground
  const strip = (width, x, y, material, period) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(width, ROAD_LEN), material);
    m.rotation.x = -Math.PI / 2; m.position.set(x, y, 0); m.receiveShadow = true; world.add(m); followers.push(m);
    if (period) for (const k of ['map', 'normalMap', 'roughnessMap']) if (material[k]) anchored.push({ mesh: m, t: material[k], period });
    return m;
  };
  const beam = (w, h, x, y, material) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, ROAD_LEN), material); m.position.set(x, y, 0); m.castShadow = m.receiveShadow = true; world.add(m); followers.push(m); return m; };

  strip(CARRIAGE, 0, 0, onRoad(asphalt, HOLE), TILE);
  strip(CARRIAGE, 0, 0.004, onRoad(new THREE.MeshStandardMaterial(decal({ map: macroTexture(), roughness: 0.9, envMapIntensity: 0.3 })), HOLE), MACRO_LEN);
  const solidPaint = onRoad(new THREE.MeshStandardMaterial(decal({ map: paintTexture(false), roughness: 0.75, polygonOffsetFactor: -3 })), HOLE);
  const dashPaint = onRoad(new THREE.MeshStandardMaterial(decal({ map: paintTexture(true), roughness: 0.75, polygonOffsetFactor: -3 })), HOLE);
  for (const s of [-1, 1]) {
    strip(0.15, s * (HALF - 0.25), 0.008, solidPaint, 14); strip(0.15, s * (MEDIAN / 2 + 0.22), 0.008, solidPaint, 14);
    strip(0.15, s * (MEDIAN / 2 + EDGE + LANE), 0.008, dashPaint, 9);
  }

  // Kerbs in black and yellow, a raised median, and paved footpaths
  const concrete = new THREE.MeshStandardMaterial({ map: colorTex(speckle(256, 150, 30, [6, 3, -4]), [1, 60]), roughness: 0.95, envMapIntensity: 0.3 });
  const kerbPaint = onRoad(new THREE.MeshStandardMaterial({ roughness: 0.8, envMapIntensity: 0.3 }), STRIPE);
  const paver = (() => {
    const S = 256, [c, g] = canvas(S, S);
    for (let y = 0; y < 8; y++) for (let x = 0; x < 4; x++) { const v = 128 + Math.random() * 40; g.fillStyle = `rgb(${v + 8 | 0},${v | 0},${v - 10 | 0})`; g.fillRect(x * 64 + (y % 2 ? 32 : 0) - 32, y * 32, 62, 30); g.fillRect(x * 64 + (y % 2 ? 32 : 0) + 224, y * 32, 62, 30); }
    const img = g.getImageData(0, 0, S, S); for (let i = 0; i < S * S * 4; i += 4) { const n = (Math.random() - 0.5) * 22; img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n; } g.putImageData(img, 0, 0);
    return c;
  })();
  beam(MEDIAN - 0.3, 0.3, 0, 0.15, concrete);
  for (const s of [-1, 1]) {
    beam(0.16, 0.32, s * (MEDIAN / 2 - 0.08), 0.16, kerbPaint);
    beam(0.3, 0.2, s * (HALF + 0.15), 0.1, kerbPaint);
    strip(FOOT - 0.3, s * (HALF + 0.3 + (FOOT - 0.3) / 2), 0.19, new THREE.MeshStandardMaterial({ map: colorTex(paver, [(FOOT - 0.3) / 1.6, ROAD_LEN / 1.6]), roughness: 0.95, envMapIntensity: 0.3 }), 1.6);
  }
  // open ground beyond the footpaths: compacted earth and dust
  for (const s of [-1, 1]) strip(320, s * (HALF + 0.2 + 160), -0.02, new THREE.MeshStandardMaterial({ map: colorTex(speckle(256, 138, 36, [12, 4, -12]), [320 / 6, ROAD_LEN / 6]), roughness: 1, envMapIntensity: 0.25 }), 6);

  // ------------------------------------------------------------------ planting: leaf cards on branches (street trees) and median shrubs
  const leafTex = (() => {
    const [c, g] = canvas(256, 256);
    for (let i = 0; i < 170; i++) {
      const x = 22 + Math.random() * 212, y = 22 + Math.random() * 212; if (Math.hypot(x - 128, y - 128) > 112) continue;
      g.save(); g.translate(x, y); g.rotate(Math.random() * 6.28);
      g.fillStyle = `hsl(${82 + Math.random() * 28},${24 + Math.random() * 16}%,${15 + Math.random() * 17}%)`;
      g.beginPath(); g.ellipse(0, 0, 9 + Math.random() * 9, 4 + Math.random() * 4, 0, 0, 6.28); g.fill(); g.restore();
    }
    return colorTex(c);
  })();
  const barkMat = new THREE.MeshStandardMaterial({ color: 0x2b241e, roughness: 1, envMapIntensity: 0.15 });
  const leafMat = twoSided(new THREE.MeshStandardMaterial({ map: leafTex, color: 0xd9dcc4, alphaTest: 0.42, side: THREE.DoubleSide, roughness: 0.9, envMapIntensity: 0.4 }));
  const leafDepth = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: leafTex, alphaTest: 0.42 });
  function leafCards(A, cc, size, count, centre) {
    for (let i = 0; i < count; i++) {
      const o = new V3(range(-1, 1), range(-0.8, 0.8), range(-1, 1)).normalize().multiplyScalar(size * range(0.25, 1)).add(cc);
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(rnd() * 3.14, rnd() * 3.14, rnd() * 3.14)), s = size * range(0.45, 0.8);
      const n = o.clone().sub(centre).normalize().lerp(new V3(0, 1, 0), 0.25).normalize(), base = A.P.length / 3;
      for (const [cx, cy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { const v = new V3(cx * s, cy * s, 0).applyQuaternion(q).add(o); A.P.push(v.x, v.y, v.z); A.N.push(n.x, n.y, n.z); A.U.push(cx * 0.5 + 0.5, cy * 0.5 + 0.5); }
      A.I.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  }
  const cardGeo = (A) => { const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(A.P, 3)); geo.setAttribute('normal', new THREE.Float32BufferAttribute(A.N, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(A.U, 2)); geo.setIndex(A.I); return geo; };
  function treeModel() {
    const height = range(6, 9), spread = range(2.2, 3.4), g = new THREE.Group(), A = { P: [], N: [], U: [], I: [] };
    const limb = (from, to, r0, r1) => { const dir = to.clone().sub(from), geo = new THREE.CylinderGeometry(r1, r0, dir.length(), 7, 1); geo.translate(0, dir.length() / 2, 0); const m = new THREE.Mesh(geo, barkMat); m.position.copy(from); m.quaternion.setFromUnitVectors(new V3(0, 1, 0), dir.normalize()); m.castShadow = true; g.add(m); };
    const fork = new V3(range(-0.3, 0.3), height * range(0.4, 0.5), range(-0.3, 0.3)), centre = new V3(0, height * 0.72, 0);
    limb(new V3(0, -0.3, 0), fork, 0.26, 0.18);
    for (let k = 0; k < 11; k++) {
      const a = rnd() * 6.28, e = range(-0.25, 1), rr = spread * range(0.45, 1);
      const cc = new V3(Math.cos(a) * rr * Math.cos(e * 0.9), height * 0.72 + Math.sin(e) * height * 0.26, Math.sin(a) * rr * Math.cos(e * 0.9));
      if (k < 5) limb(fork, cc.clone().lerp(fork, 0.25), 0.13, 0.04);
      leafCards(A, cc, range(1.3, 2.0), 34, centre);
    }
    const leaves = new THREE.Mesh(cardGeo(A), leafMat); leaves.castShadow = true; leaves.customDepthMaterial = leafDepth; g.add(leaves);
    return mergeParts(g);
  }
  const scenery = [], treeKinds = Array.from({ length: 4 }, treeModel);
  for (let i = 0; i < 9; i++) { const t = treeKinds[i % 4].clone(); t.traverse((o) => { if (o.material === leafMat) o.customDepthMaterial = leafDepth; }); t.rotation.y = rnd() * 6.28; t.scale.setScalar(range(0.6, 0.8)); scenery.push({ obj: t, x: (i % 2 ? 1 : -1) * (HALF + FOOT - 0.5), z0: i * (WINDOW / 9) + range(-6, 6) }); world.add(t); }
  const shrubA = { P: [], N: [], U: [], I: [] }; leafCards(shrubA, new V3(0, 0.62, 0), 0.42, 40, new V3(0, 0.3, 0));
  const SHRUBS = Math.ceil(WINDOW / 2.2), shrubs = new THREE.InstancedMesh(cardGeo(shrubA), leafMat, SHRUBS);
  shrubs.castShadow = true; shrubs.customDepthMaterial = leafDepth; shrubs.frustumCulled = false; world.add(shrubs);
  const dummy = new THREE.Object3D();
  function mergeParts(group) { // meshes with one shared material are baked into a single mesh
    const by = new Map();
    for (const c of [...group.children]) {
      if (!c.isMesh || Array.isArray(c.material) || !c.geometry.index || !c.geometry.attributes.uv || !c.geometry.attributes.normal || c.renderOrder) continue;
      const k = c.material.uuid + (c.castShadow ? 's' : '') + (c.customDepthMaterial ? 'd' : '');
      if (!by.has(k)) by.set(k, []);
      by.get(k).push(c);
    }
    for (const list of by.values()) {
      if (list.length < 2) continue;
      const geos = list.map((m) => { m.updateMatrix(); const g = m.geometry.clone().applyMatrix4(m.matrix); for (const n of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(n)) g.deleteAttribute(n); return g; });
      const merged = new THREE.Mesh(BufferGeometryUtils.mergeBufferGeometries(geos), list[0].material);
      merged.castShadow = list[0].castShadow; merged.receiveShadow = list[0].receiveShadow; geos.forEach((g) => g.dispose());
      for (const m of list) group.remove(m);
      group.add(merged);
    }
    return group;
  }

  // ------------------------------------------------------------------ street furniture: median lights and speed signs
  const steel = shiny(new THREE.MeshStandardMaterial({ color: 0x8f969c, roughness: 0.5, metalness: 0.9, envMapIntensity: 0.9 }));
  const lensMat = new THREE.MeshStandardMaterial({ color: 0xe9eef2, roughness: 0.3, metalness: 0.2, emissive: 0xffe2a8, emissiveIntensity: 0 });
  const glowTex = (() => { const [c, g] = canvas(128, 128), gr = g.createRadialGradient(64, 64, 2, 64, 64, 62); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.45, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return colorTex(c); })();
  const lightMat = (color) => new THREE.MeshBasicMaterial({ map: glowTex, color, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6 });
  const lampPoolMat = lightMat(0xffd9a0), beamMat = lightMat(0xfff0d0), poolGeo = new THREE.PlaneGeometry(17, 17), beamGeo = new THREE.PlaneGeometry(5, 13);
  const onRoadLight = (geo, mat, x, z) => { const m = new THREE.Mesh(geo, mat); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.04, z); m.renderOrder = 4; m.visible = false; lights.push(m); return m; };
  const lights = [];
  function lampPost() { // one pole in the median with an arm over each carriageway
    const g = new THREE.Group(), pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.11, 8.0, 12), steel); pole.position.y = 4.0; pole.castShadow = true; g.add(pole);
    for (const s of [-1, 1]) {
      const curve = new THREE.QuadraticBezierCurve3(new V3(0, 7.8, 0), new V3(s * 0.4, 8.8, 0), new V3(s * 2.6, 8.6, 0));
      const arm = new THREE.Mesh(new THREE.TubeGeometry(curve, 12, 0.045, 8), steel), head = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.1, 0.3), steel), lens = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.02, 0.22), lensMat);
      arm.castShadow = head.castShadow = true; head.position.set(s * 2.9, 8.57, 0); lens.position.set(s * 2.9, 8.51, 0); g.add(arm, head, lens, onRoadLight(poolGeo, lampPoolMat, s * 3.4, 0));
    }
    return mergeParts(g);
  }
  for (let i = 0; i < 9; i++) { const p = lampPost(); scenery.push({ obj: p, x: 0, z0: i * (WINDOW / 9) + 6 }); world.add(p); }
  const signTex = (draw, w, h) => { const [c, g] = canvas(w, h); draw(g); return colorTex(c); };
  const speedTex = signTex((c) => { c.fillStyle = '#fff'; c.beginPath(); c.arc(64, 64, 62, 0, 6.3); c.fill(); c.strokeStyle = '#c8102e'; c.lineWidth = 14; c.beginPath(); c.arc(64, 64, 52, 0, 6.3); c.stroke(); c.fillStyle = '#111'; c.font = 'bold 54px sans-serif'; c.textAlign = 'center'; c.fillText('50', 64, 84); }, 128, 128);
  for (const z0 of [60, 230]) {
    const g = new THREE.Group(), pole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 2.9, 8), steel); pole.position.y = 1.45; pole.castShadow = true;
    const disc = new THREE.Mesh(new THREE.CircleGeometry(0.38, 24), new THREE.MeshStandardMaterial({ map: speedTex, roughness: 0.6 })); disc.position.set(0, 2.7, 0.03);
    g.add(pole, disc); scenery.push({ obj: g, x: -(HALF + 0.75), z0 }); world.add(g);
  }

  // ------------------------------------------------------------------ buildings: apartment and office blocks with shops at street level
  const BAY = 3.2, FLOOR = 3.1;
  function facade(kind, tone) { // one tile = 4 bays x 4 floors
    const S = 512, [c, g] = canvas(S, S), [ec, eg] = canvas(S, S), w = S / 4, h = S / 4;
    eg.fillStyle = '#000'; eg.fillRect(0, 0, S, S); // windows that are lit after dark
    g.fillStyle = kind === 'office' ? '#4d6474' : tone; g.fillRect(0, 0, S, S);
    for (let fy = 0; fy < 4; fy++) for (let bx = 0; bx < 4; bx++) {
      const x = bx * w, y = fy * h;
      if (kind === 'office') {
        const gl = g.createLinearGradient(x, y, x + w, y + h); const v = 70 + Math.random() * 50;
        gl.addColorStop(0, `rgb(${v * 0.9 | 0},${v | 0},${v * 1.1 | 0})`); gl.addColorStop(1, `rgb(${v * 0.62 | 0},${v * 0.72 | 0},${v * 0.82 | 0})`);
        g.fillStyle = gl; g.fillRect(x + 3, y + 3, w - 6, h - 26); if (Math.random() < 0.3) { eg.fillStyle = '#b9c6d8'; eg.fillRect(x + 3, y + 3, w - 6, h - 26); } g.fillStyle = '#39444c'; g.fillRect(x, y + h - 24, w, 24);
        g.fillStyle = 'rgba(20,26,30,0.9)'; g.fillRect(x + w / 2 - 1, y, 3, h - 24);
      } else {
        g.fillStyle = 'rgba(0,0,0,0.16)'; g.fillRect(x, y + h - 9, w, 9);                                   // floor slab line
        const wx = x + 22, wy = y + 22, ww = w - 44, wh = h - 62;
        g.fillStyle = '#e9e6de'; g.fillRect(wx - 4, wy - 4, ww + 8, wh + 8);                                 // frame
        g.fillStyle = ['#1c242c', '#232b33', '#2b3138', '#3a3327'][Math.random() * 4 | 0]; g.fillRect(wx, wy, ww, wh);
        if (Math.random() < 0.4) { eg.fillStyle = ['#ffd9a0', '#ffe7c2', '#f1c183'][Math.random() * 3 | 0]; eg.fillRect(wx, wy, ww, wh); }
        if (Math.random() < 0.35) { g.fillStyle = `hsla(${Math.random() * 360 | 0},16%,58%,0.5)`; g.fillRect(wx, wy, ww * (0.4 + Math.random() * 0.4), wh); } // curtain
        g.fillStyle = 'rgba(255,255,255,0.14)'; g.fillRect(wx + ww / 2 - 1, wy, 2, wh);
        if (kind === 'balcony') { g.fillStyle = 'rgba(0,0,0,0.28)'; g.fillRect(x + 6, y + h - 40, w - 12, 5); g.strokeStyle = 'rgba(40,40,40,0.75)'; g.lineWidth = 1.5; for (let k = 0; k < 9; k++) { g.beginPath(); g.moveTo(x + 8 + k * (w - 16) / 8, y + h - 40); g.lineTo(x + 8 + k * (w - 16) / 8, y + h - 12); g.stroke(); } }
        if (Math.random() < 0.4) { g.fillStyle = '#d8dad8'; g.fillRect(x + w - 40, y + h - 34, 28, 18); g.fillStyle = 'rgba(0,0,0,0.3)'; g.fillRect(x + w - 40, y + h - 16, 28, 3); } // AC unit
      }
    }
    for (let i = 0; i < 90; i++) { g.fillStyle = `rgba(45,38,28,${(0.03 + Math.random() * 0.07).toFixed(3)})`; g.fillRect(Math.random() * S, Math.random() * S, 2 + Math.random() * 5, 30 + Math.random() * 150); } // rain streaks
    const t = colorTex(c, [1, 1]); t.lit = colorTex(ec, [1, 1]); return t;
  }
  const TONES = ['#c4baa8', '#cdbfaa', '#b9c0c2', '#cfc5b3', '#c2b09e', '#b3bcae', '#c8c8c3', '#bfa998'];
  const facadeMats = [];
  for (const tone of TONES) for (const kind of ['plain', 'balcony']) facadeMats.push(new THREE.MeshStandardMaterial({ map: facade(kind, tone), roughness: 0.92, envMapIntensity: 0.35 }));
  const officeMats = [0, 1].map(() => shiny(new THREE.MeshStandardMaterial({ map: facade('office'), roughness: 0.22, metalness: 0.5, envMapIntensity: 1.1 })));
  const shopMats = [0, 1, 2].map(() => { // shutters, open shop fronts and signboards
    const [c, g] = canvas(512, 128);
    for (let s = 0; s < 4; s++) {
      const x = s * 128; g.fillStyle = `hsl(${Math.random() * 360 | 0},${14 + Math.random() * 20 | 0}%,${26 + Math.random() * 18 | 0}%)`; g.fillRect(x + 3, 4, 122, 38);
      g.fillStyle = 'rgba(255,255,255,0.9)'; g.fillRect(x + 14, 14, 50 + Math.random() * 46, 9); g.fillRect(x + 14, 28, 30 + Math.random() * 30, 5);
      if (Math.random() < 0.45) { g.fillStyle = '#17191b'; g.fillRect(x + 6, 46, 116, 82); g.fillStyle = 'rgba(255,220,160,0.18)'; g.fillRect(x + 6, 46, 116, 30); }
      else { g.fillStyle = '#8a8f92'; g.fillRect(x + 6, 46, 116, 82); g.fillStyle = 'rgba(0,0,0,0.22)'; for (let y = 50; y < 128; y += 6) g.fillRect(x + 6, y, 116, 2); }
      g.fillStyle = '#c9c4b8'; g.fillRect(x, 0, 4, 128);
    }
    return new THREE.MeshStandardMaterial({ map: colorTex(c, [1, 1]), roughness: 0.8, envMapIntensity: 0.3 });
  });
  for (const m of [...facadeMats, ...officeMats]) { m.emissiveMap = m.map.lit; m.emissive.set(0xffffff); m.emissiveIntensity = 0; }
  for (const m of shopMats) { m.emissiveMap = m.map; m.emissive.set(0xffffff); m.emissiveIntensity = 0; }
  const roofMat = new THREE.MeshStandardMaterial({ color: 0x8b8880, roughness: 1 }), tankMat = new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.6 });
  const tankGeo = new THREE.CylinderGeometry(0.75, 0.8, 1.5, 14);
  const scaleUV = (geo, face, su, sv, ou) => { const uv = geo.attributes.uv; for (let i = face * 4; i < face * 4 + 4; i++) uv.setXY(i, uv.getX(i) * su + ou, uv.getY(i) * sv); };
  function building(len, depth, floors, kind, toward) { // len runs along the road; `toward` is the side facing it
    const h = floors * FLOOR, g = new THREE.Group(), geo = new THREE.BoxGeometry(depth, h, len), ou = Math.floor(rnd() * 4) / 4;
    for (const f of [0, 1]) scaleUV(geo, f, len / (BAY * 4), floors / 4, ou); for (const f of [4, 5]) scaleUV(geo, f, depth / (BAY * 4), floors / 4, ou);
    const wall = kind === 'office' ? officeMats[rnd() * 2 | 0] : facadeMats[rnd() * facadeMats.length | 0];
    const box = new THREE.Mesh(geo, [wall, wall, roofMat, roofMat, wall, wall]); box.position.y = h / 2; box.castShadow = box.receiveShadow = true; g.add(box);
    if (kind !== 'office') { const sg = new THREE.BoxGeometry(0.5, 3.5, len - 0.3); for (const f of [0, 1]) scaleUV(sg, f, len / 14, 1, 0); const shop = new THREE.Mesh(sg, shopMats[rnd() * 3 | 0]); shop.position.set(toward * (depth / 2 + 0.2), 1.75, 0); g.add(shop); }
    const parapet = new THREE.Mesh(new THREE.BoxGeometry(depth + 0.3, 0.5, len + 0.3), roofMat); parapet.position.y = h + 0.1; g.add(parapet);
    for (let k = 0; k < 1 + (rnd() * 3 | 0); k++) { const t = new THREE.Mesh(tankGeo, tankMat); t.position.set(range(-depth / 3, depth / 3), h + 1.6, range(-len / 3, len / 3)); g.add(t); }
    const stair = new THREE.Mesh(new THREE.BoxGeometry(3, 2.6, 3.4), roofMat); stair.position.set(range(-1, 1), h + 1.4, range(-len / 4, len / 4)); g.add(stair);
    return mergeParts(g);
  }
  for (const side of [-1, 1]) {
    let z = 0;
    while (z < WINDOW - 12) {
      const len = Math.min(range(11, 24), WINDOW - z - 2), depth = range(10, 16), tall = rnd() < 0.22, floors = tall ? 9 + (rnd() * 6 | 0) : 3 + (rnd() * 5 | 0);
      const b = building(len, depth, floors, tall && rnd() < 0.5 ? 'office' : 'apt', -side);
      scenery.push({ obj: b, x: side * (HALF + FOOT + 0.6 + depth / 2 + range(0, 2.2)), z0: z + len / 2 }); world.add(b); z += len + range(0.8, 4.5);
    }
    for (let k = 0; k < 7; k++) { const b = building(range(16, 28), range(14, 20), 12 + (rnd() * 11 | 0), rnd() < 0.45 ? 'office' : 'apt', -side); scenery.push({ obj: b, x: side * (HALF + FOOT + 40 + range(0, 30)), z0: range(0, WINDOW) }); world.add(b); }
  }

  // ------------------------------------------------------------------ vehicles: lofted bodies with flush glass, wheels, lamps, mirrors
  const glassMat = shiny(new THREE.MeshStandardMaterial({ color: 0x0b0f13, roughness: 0.06, metalness: 0.9, envMapIntensity: 1.6 }));
  const trimMat = new THREE.MeshStandardMaterial({ color: 0x17181a, roughness: 0.7, envMapIntensity: 0.5 });
  const archMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 1, envMapIntensity: 0 });
  const headMat = shiny(new THREE.MeshStandardMaterial({ color: 0xf2f4f6, roughness: 0.1, metalness: 0.6, envMapIntensity: 1.8 }));
  const tailMat = new THREE.MeshStandardMaterial({ color: 0x6e0606, roughness: 0.22, metalness: 0.3, emissive: 0x3a0000, emissiveIntensity: 0.35, envMapIntensity: 0.8 });
  const tyreMat = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.92, envMapIntensity: 0.25 });
  const rimMat = new THREE.MeshStandardMaterial({ map: signTex((g) => {
    g.translate(128, 128); g.fillStyle = '#121212'; g.beginPath(); g.arc(0, 0, 128, 0, 6.28); g.fill(); g.fillStyle = '#b9bdc2'; g.beginPath(); g.arc(0, 0, 100, 0, 6.28); g.fill(); g.fillStyle = '#1a1a1b';
    for (let i = 0; i < 5; i++) { g.save(); g.rotate((i / 5) * 6.28 + 0.628); g.beginPath(); g.moveTo(14, -30); g.quadraticCurveTo(52, -66, 88, -30); g.lineTo(88, 30); g.quadraticCurveTo(52, 66, 14, 30); g.closePath(); g.fill(); g.restore(); }
    g.fillStyle = '#6f7378'; g.beginPath(); g.arc(0, 0, 17, 0, 6.28); g.fill();
  }, 256, 256), roughness: 0.35, metalness: 0.7 });
  const WHEEL_R = 0.345, tyreGeo = new THREE.LatheGeometry([[0.19, -0.115], [0.3, -0.115], [0.335, -0.08], [0.345, 0], [0.335, 0.08], [0.3, 0.115], [0.19, 0.115]].map(([x, y]) => new THREE.Vector2(x, y)), 24);
  tyreGeo.rotateZ(Math.PI / 2);
  const rimGeo = new THREE.CircleGeometry(0.255, 24), archGeo = new THREE.CircleGeometry(0.44, 24), lampGeo = new THREE.SphereGeometry(1, 12, 8), plateGeo = new THREE.BoxGeometry(0.5, 0.12, 0.02);
  const mirrorGeo = new THREE.SphereGeometry(0.1, 10, 8); mirrorGeo.scale(1.15, 0.7, 0.55);
  const plateMat = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.6 });
  const blobMat = new THREE.MeshBasicMaterial(decal({ map: signTex((g) => { g.translate(64, 128); g.scale(1, 2); const gr = g.createRadialGradient(0, 0, 8, 0, 0, 62); gr.addColorStop(0, 'rgba(0,0,0,0.62)'); gr.addColorStop(0.6, 'rgba(0,0,0,0.4)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(-64, -64, 128, 128); }, 128, 256), polygonOffsetFactor: -5 }));

  // top: roofline control points [z, y] from tail to nose; cabin: z of rear-glass base, roof start, roof end, screen base
  const BODIES = {
    sedan: { L: 4.55, W: 1.8, belt: 0.95, wheelZ: 1.38, top: [[-2.28, .72], [-2.2, .98], [-1.6, 1.04], [-.98, 1.4], [-.2, 1.45], [.38, 1.43], [1.08, 1.03], [1.9, .93], [2.2, .78], [2.28, .62]], cabin: [-1.6, -.98, .38, 1.08] },
    hatch: { L: 3.9, W: 1.7, belt: 0.98, wheelZ: 1.22, top: [[-1.95, .78], [-1.92, 1.08], [-1.78, 1.32], [-1.28, 1.5], [-.2, 1.52], [.3, 1.5], [.95, 1.06], [1.64, .95], [1.9, .8], [1.95, .64]], cabin: [-1.9, -1.28, .3, .95] },
    suv: { L: 4.6, W: 1.88, belt: 1.12, wheelZ: 1.4, top: [[-2.3, .9], [-2.27, 1.3], [-2.15, 1.62], [-1.72, 1.74], [-.2, 1.76], [.42, 1.73], [1.1, 1.24], [1.96, 1.12], [2.24, .95], [2.3, .74]], cabin: [-2.25, -1.72, .42, 1.1] },
    auto: { L: 2.7, W: 1.34, belt: 0.86, wheelZ: 0.98, wheelR: 0.24, three: true, top: [[-1.35, .55], [-1.33, 1.25], [-1.2, 1.64], [-.3, 1.74], [.42, 1.7], [.92, 1.06], [1.22, .78], [1.35, .5]], cabin: [-1.28, -1.05, .42, .92] },
    bus: { L: 10.6, W: 2.5, belt: 1.55, wheelZ: 3.3, wheelR: 0.5, clear: 0.38, pillarStep: 1.5, top: [[-5.3, 1.2], [-5.27, 2.7], [-5.1, 3.05], [0, 3.1], [4.5, 3.06], [5.1, 1.75], [5.26, 1.3], [5.3, 0.9]], cabin: [-5.2, -5.0, 4.5, 5.08] },
    truck: { L: 7.4, W: 2.4, belt: 1.5, wheelZ: 2.5, wheelR: 0.48, clear: 0.42, top: [[-3.7, 1.3], [-3.68, 2.9], [-3.5, 3.0], [1.55, 3.0], [1.72, 2.55], [3.0, 2.5], [3.46, 1.62], [3.64, 1.2], [3.7, 0.9]], cabin: [1.75, 1.86, 3.0, 3.44] },
  };
  const FY = [0, 0.1, 0.34, 0.6, 0.8, 0.92, 0.98, 1], FX = [1, 1, 0.985, 0.95, 0.9, 0.76, 0.46, 0], LOWER = 5, RING = LOWER + FY.length;
  function bodyGeometry(b) {
    const NS = b.L > 6 ? 72 : 56, half = b.L / 2, clear = b.clear || 0.2, boxy = b.L > 6;
    const topAt = (z) => { const t = b.top; for (let i = 1; i < t.length; i++) if (z <= t[i][0]) return lerp(t[i - 1][1], t[i][1], (z - t[i - 1][0]) / (t[i][0] - t[i - 1][0])); return t[t.length - 1][1]; };
    const stations = [];
    for (let s = 0; s <= NS; s++) { const u = Math.sin((s / NS - 0.5) * Math.PI); stations.push({ u, z: u * half * 0.999 }); }
    for (const st of stations) st.top = topAt(st.z);
    for (let pass = 0; pass < (boxy ? 1 : 2); pass++) for (let s = 1; s < NS; s++) stations[s].top = (stations[s - 1].top + stations[s].top * 2 + stations[s + 1].top) / 4;
    const pos = [], ringLen = RING * 2 - 2, pow = boxy ? 14 : 6;
    for (const st of stations) {
      const w = (b.W / 2) * Math.pow(Math.max(0, 1 - Math.pow(Math.abs(st.u), pow)), 1 / pow), bot = clear + 0.14 * Math.pow(Math.abs(st.u), 8);
      const belt = Math.min(b.belt, st.top - 0.03), cabin = clamp((st.top - belt - 0.05) / 0.3, 0, 1), wu = w * (boxy ? 0.985 : 0.97 - 0.15 * cabin);
      const halfRing = [[0, bot], [w * 0.8, bot], [w * 0.97, bot + 0.07], [w, bot + 0.22], [w, (bot + belt) / 2 + 0.06]];
      FY.forEach((fy, k) => halfRing.push([k === 0 ? w * 0.99 : lerp(w * 0.99, wu * (boxy ? Math.pow(FX[k], 0.35) : FX[k]), Math.min(1, k / 2)), belt + (st.top - belt) * fy]));
      st.cabin = cabin; st.w = w;
      for (const [x, y] of halfRing.concat(halfRing.slice(1, -1).reverse().map(([x, y]) => [-x, y]))) pos.push(x, y, st.z);
    }
    const [zRearBase, zRoof0, zRoof1, zFrontBase] = b.cabin, groups = { paint: [], glass: [], trim: [] };
    for (let s = 0; s < NS; s++) for (let j = 0; j < ringLen; j++) {
      const a = s * ringLen + j, bb = s * ringLen + ((j + 1) % ringLen), c = a + ringLen, d = bb + ringLen;
      const cx = (pos[a * 3] + pos[bb * 3] + pos[c * 3] + pos[d * 3]) / 4, cy = (pos[a * 3 + 1] + pos[bb * 3 + 1] + pos[c * 3 + 1] + pos[d * 3 + 1]) / 4, cz = (pos[a * 3 + 2] + pos[c * 3 + 2]) / 2;
      const st = stations[s], k = (j < RING - 1 ? j : ringLen - 1 - j) - LOWER, ax = Math.abs(cx), u = cz / half;
      const inCabin = cz > zRearBase + 0.06 && cz < zFrontBase - 0.06 && st.cabin > 0.6, screen = cz > zRoof1 || cz < zRoof0;
      let pillar = (cz > -0.16 && cz < -0.04) || Math.abs(cz - zRoof0) < 0.07 || Math.abs(cz - zRoof1) < 0.07;
      if (b.pillarStep) pillar = pillar || Math.abs((((cz % b.pillarStep) + b.pillarStep) % b.pillarStep) - b.pillarStep / 2) > b.pillarStep / 2 - 0.07;
      let kind = 'paint';
      if (inCabin && k >= 1 && (screen ? ax < st.w * 0.74 || k <= 3 : k <= 3) && !(pillar && k <= 3 && !(screen && ax < st.w * 0.74))) kind = 'glass';
      if (cy < clear + 0.16 || (Math.abs(u) > 0.93 && cy < clear + 0.28)) kind = 'trim';
      groups[kind].push(a, bb, c, bb, d, c);
    }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    const index = []; let start = 0;
    Object.keys(groups).forEach((key, m) => { geo.addGroup(start, groups[key].length, m); index.push(...groups[key]); start += groups[key].length; });
    geo.setIndex(index); geo.computeVertexNormals(); return geo;
  }
  const bodyGeos = {}; for (const k in BODIES) bodyGeos[k] = bodyGeometry(BODIES[k]);
  const paints = {}; const paintOf = (color) => paints[color] || (paints[color] = shiny(new THREE.MeshPhysicalMaterial({ color, roughness: 0.3, metalness: 0.55, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 1.25 })));
  const autoPaint = new THREE.MeshStandardMaterial({ color: 0x0d0f0d, roughness: 0.55, metalness: 0.1, envMapIntensity: 0.4 }), hoodMat = new THREE.MeshStandardMaterial({ color: 0xc99700, roughness: 0.7, envMapIntensity: 0.3 });
  const heavy = {}, heavyPaint = (color) => heavy[color] || (heavy[color] = new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.2, envMapIntensity: 0.5 }));
  function makeVehicle(kind, color) {
    if (kind === 'bike') return makeBike(color);
    const b = BODIES[kind], car = new THREE.Group(), paint = kind === 'auto' ? autoPaint : b.L > 6 ? heavyPaint(color) : paintOf(color), wr = (b.wheelR || WHEEL_R) / WHEEL_R;
    const body = new THREE.Mesh(bodyGeos[kind], [paint, glassMat, trimMat]); body.castShadow = true; car.add(body);
    car.wheels = [];
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      if (b.three && sz > 0 && sx > 0) continue; // an auto-rickshaw has one front wheel
      const x = b.three && sz > 0 ? 0 : sx * (b.W / 2 - 0.13 * wr), wheel = new THREE.Group(), tyre = new THREE.Mesh(tyreGeo, tyreMat); tyre.castShadow = true;
      const rim = new THREE.Mesh(rimGeo, rimMat); rim.rotation.y = sx * Math.PI / 2; rim.position.x = sx * 0.118;
      wheel.add(tyre, rim); wheel.scale.setScalar(wr); wheel.position.set(x, WHEEL_R * wr, sz * b.wheelZ); car.add(wheel); car.wheels.push(wheel);
      if (!b.three || sz < 0) { const arch = new THREE.Mesh(archGeo, archMat); arch.scale.setScalar(wr); arch.rotation.y = sx * Math.PI / 2; arch.position.set(sx * (b.W / 2 - 0.012), WHEEL_R * wr + 0.02, sz * b.wheelZ); car.add(arch); }
    }
    const noseY = b.top[b.top.length - 2][1], tailY = Math.min(b.belt, b.top[1][1]);
    for (const sx of [-1, 1]) {
      const head = new THREE.Mesh(lampGeo, headMat); head.scale.set(0.22, 0.08, 0.14); head.rotation.y = -sx * 0.5; head.position.set(sx * b.W * 0.31, Math.min(noseY, b.belt) - 0.12, b.L / 2 - 0.2); car.add(head);
      const tail = new THREE.Mesh(lampGeo, tailMat); tail.scale.set(0.2, 0.1, 0.12); tail.rotation.y = sx * 0.5; tail.position.set(sx * b.W * 0.33, tailY - 0.14, -b.L / 2 + 0.16); car.add(tail);
      const mirror = new THREE.Mesh(mirrorGeo, paint); mirror.position.set(sx * (b.W / 2 + 0.03), b.belt + 0.08, b.cabin[3] - 0.22); car.add(mirror);
    }
    for (const sz of [-1, 1]) { const plate = new THREE.Mesh(plateGeo, plateMat); plate.position.set(0, (b.clear || 0.2) + 0.32, sz * (b.L / 2 - 0.012)); car.add(plate); }
    if (kind === 'auto') { const roof = new THREE.Mesh(new THREE.BoxGeometry(b.W * 0.9, 0.16, 1.5), hoodMat); roof.position.set(0, 1.64, -0.42); roof.castShadow = true; car.add(roof); }
    car.add(onRoadLight(beamGeo, beamMat, 0, b.L / 2 + 5.6));
    const blob = new THREE.Mesh(new THREE.PlaneGeometry(b.W + 0.9, b.L + 0.9), blobMat); blob.rotation.x = -Math.PI / 2; blob.position.y = 0.02; blob.renderOrder = 3; car.add(blob);
    mergeParts(car);
    car.detail = car.children.filter((c) => c !== body && c !== blob && !car.wheels.includes(c));
    return car;
  }
  const riderGeo = new THREE.CylinderGeometry(0.17, 0.2, 0.62, 10), helmetGeo = new THREE.SphereGeometry(0.135, 12, 10);
  function makeBike(color) { // motorcycle with a rider
    const g = new THREE.Group(); g.wheels = [];
    for (const sz of [-0.66, 0.66]) { const w = new THREE.Group(), t = new THREE.Mesh(tyreGeo, tyreMat); t.scale.set(0.45, 0.88, 0.88); t.castShadow = true; w.add(t); w.position.set(0, 0.3, sz); g.add(w); g.wheels.push(w); }
    const part = (geo, mat, x, y, z, rx) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); if (rx) m.rotation.x = rx; m.castShadow = true; g.add(m); return m; };
    part(new THREE.BoxGeometry(0.2, 0.3, 1.15), trimMat, 0, 0.55, 0); part(new THREE.BoxGeometry(0.26, 0.09, 0.62), trimMat, 0, 0.84, -0.32);
    const tank = part(lampGeo, paintOf(color), 0, 0.84, 0.2); tank.scale.set(0.17, 0.14, 0.3);
    part(new THREE.CylinderGeometry(0.03, 0.03, 0.62, 6), steel, 0, 1.02, 0.5).rotation.z = Math.PI / 2;
    part(riderGeo, new THREE.MeshStandardMaterial({ color: [0x39485a, 0x6b6f76, 0x2f3a2c, 0x7a4b3a][rnd() * 4 | 0], roughness: 0.9 }), 0, 1.22, -0.14, 0.28);
    part(helmetGeo, trimMat, 0, 1.64, 0.0); part(new THREE.BoxGeometry(0.4, 0.2, 0.5), trimMat, 0, 0.88, -0.04);
    part(lampGeo, headMat, 0, 0.98, 0.6).scale.set(0.07, 0.07, 0.05); part(lampGeo, tailMat, 0, 0.82, -0.7).scale.set(0.06, 0.04, 0.03);
    const beam = onRoadLight(beamGeo, beamMat, 0, 5.2); beam.scale.set(0.6, 0.8, 1); g.add(beam);
    const blob = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 2.6), blobMat); blob.rotation.x = -Math.PI / 2; blob.position.y = 0.02; blob.renderOrder = 3; g.add(blob);
    return mergeParts(g);
  }
  // Each lane has one speed, so vehicles keep their gaps and never overlap. The kerb-side lanes are the slow ones.
  const CAM_SPEED = 9.5, WHITE = 0xe2e3e4, SILVER = 0xa9afb5, GREY = 0x4a4e54, DARK = 0x1f2226, RED = 0x7c1616, BLUE = 0x1d3350, AUTO = 0x1d1f1c, BUS = 0x7d1217, TRUCK = 0x6e4a22;
  const lanes = [
    { x: LANES_X[0], dir: -1, speed: 8.0, v: [['bus', BUS], ['auto', AUTO], ['hatch', WHITE], ['truck', TRUCK], ['auto', AUTO], ['bike', RED]] },
    { x: LANES_X[1], dir: -1, speed: 10.6, v: [['sedan', WHITE], ['suv', DARK], ['bike', BLUE], ['hatch', SILVER], ['sedan', RED], ['suv', WHITE], ['hatch', GREY]] },
    { x: LANES_X[2], dir: 1, speed: 11.5, v: [['hatch', WHITE], ['sedan', GREY], ['suv', SILVER], ['bike', DARK], ['sedan', WHITE], ['hatch', BLUE], ['suv', DARK]] },
    { x: LANES_X[3], dir: 1, speed: 8.5, v: [['truck', TRUCK], ['auto', AUTO], ['bus', BUS], ['hatch', SILVER], ['auto', AUTO], ['bike', GREY]] },
  ];
  const cars = [];
  for (const lane of lanes) lane.v.forEach(([kind, color], i) => {
    const obj = makeVehicle(kind, color); obj.rotation.y = lane.dir < 0 ? Math.PI : 0; world.add(obj);
    cars.push({ obj, lane, z0: -(i * (WINDOW / lane.v.length) + (i % 2 ? 9 : 0) + lanes.indexOf(lane) * 13) });
  });

  // ------------------------------------------------------------------ potholes: an opening cut in the road over a real hollow
  const SEVERITY = { Low: '#34d399', Medium: '#fbbf24', High: '#fb923c', Critical: '#f87171' }, DEPTH = { Low: 0.09, Medium: 0.14, High: 0.2, Critical: 0.28 };
  const HOLE_H = Math.min(8192, renderer.capabilities.maxTextureSize), [holeCanvas, hg] = canvas(512, HOLE_H);
  hg.fillStyle = '#000'; hg.fillRect(0, 0, 512, HOLE_H);
  const bowlMat = new THREE.MeshStandardMaterial({ map: colorTex(speckle(128, 62, 60, [6, 3, -3]), [1, 1]), vertexColors: true, roughness: 1, side: THREE.DoubleSide, envMapIntensity: 0.25 });
  bowlMat.map.wrapS = bowlMat.map.wrapT = THREE.RepeatWrapping;
  const stoneGeo = new THREE.DodecahedronGeometry(1, 0), stoneMat = new THREE.MeshStandardMaterial({ color: 0x3f3d3a, roughness: 1, envMapIntensity: 0.2 });
  const potholeSpecs = [['Low', 0.8, -6.6], ['Medium', 1.2, -2.3], ['High', 1.7, -5.1], ['Low', 0.7, 3.1], ['Critical', 2.4, -6.0], ['Medium', 1.25, 5.6], ['High', 1.6, -3.0], ['Medium', 1.1, 2.4], ['Critical', 2.2, -2.8], ['Low', 0.75, 6.8]];
  const N = 44;
  const potholes = potholeSpecs.map(([severity, size, x], i) => {
    const harm = [2, 3, 4, 5, 7].map((k) => [k, rnd() * 0.3 / Math.sqrt(k), rnd() * 6.283]), stretch = range(0.85, 1.35), depth = DEPTH[severity];
    const z0 = -(18 + i * (WINDOW / potholeSpecs.length) + range(-6, 6));
    const ring = Array.from({ length: N }, (_, j) => { const a = (j / N) * 6.283, r = (size / 2) * (1 + harm.reduce((s, [k, amp, ph]) => s + amp * Math.sin(k * a + ph), 0)) * (1 + (rnd() - 0.5) * 0.08); return [Math.cos(a) * r * stretch, Math.sin(a) * r]; });
    // the opening, drawn into the mask the road materials read
    const px = 512 / CARRIAGE, py = HOLE_H / WINDOW, Y0 = (((z0 % WINDOW) + WINDOW) % WINDOW) * py;
    for (const oy of [-HOLE_H, 0, HOLE_H]) { hg.beginPath(); ring.forEach(([dx, dz], j) => { const X = (x + dx + HALF) * px, Y = Y0 + dz * py + oy; j ? hg.lineTo(X, Y) : hg.moveTo(X, Y); }); hg.closePath(); hg.fillStyle = '#fff'; hg.fill(); }
    // the hollow: rim under the road edge, a steep wall, an uneven floor
    const P = [], C = [], U = [], I = [], put = (vx, vy, vz, s) => { P.push(vx, vy, vz); U.push(vx * 1.4, vz * 1.4); C.push(s, s * 0.97, s * 0.93); };
    const lit = ([dx, dz]) => { const l = Math.hypot(dx, dz) || 1; return clamp(0.5 - 0.5 * ((dx / l) * LOCAL_SUN.x + (dz / l) * LOCAL_SUN.z) / Math.hypot(LOCAL_SUN.x, LOCAL_SUN.z), 0, 1); }; // 0 under the sun-side rim
    ring.forEach((q) => put(q[0] * 1.1, -0.006, q[1] * 1.1, 0.7));
    ring.forEach((q) => put(q[0] * 0.95, -depth * 0.7, q[1] * 0.95, 0.16 + 0.62 * lit(q)));
    ring.forEach((q) => put(q[0] * 0.7, -depth * (0.9 + rnd() * 0.25), q[1] * 0.7, 0.2 + 0.4 * lit(q)));
    put(0, -depth * 1.05, 0, 0.42);
    for (let j = 0; j < N; j++) { const k = (j + 1) % N; for (const r of [0, 1]) { const a = r * N + j, b = r * N + k; I.push(a, a + N, b, b, a + N, b + N); } I.push(2 * N + j, 3 * N, 2 * N + k); }
    const bg = new THREE.BufferGeometry(); bg.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); bg.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2)); bg.setAttribute('color', new THREE.Float32BufferAttribute(C, 3)); bg.setIndex(I); bg.computeVertexNormals();
    const bowl = new THREE.Mesh(bg, bowlMat); bowl.receiveShadow = true;
    // broken surface around the opening: cracking, loosened asphalt, exposed aggregate
    const plane = size * 2.5 * Math.max(1, stretch), S = 512, [c, g] = canvas(S, S), k = S / plane, cx = S / 2;
    const blob = (m) => { g.beginPath(); ring.forEach(([dx, dz], j) => { const X = cx + dx * m * k, Y = cx + dz * m * k; j ? g.lineTo(X, Y) : g.moveTo(X, Y); }); g.closePath(); };
    const nodes = Array.from({ length: 46 }, () => { const j = Math.random() * N | 0, m = 1.08 + Math.random() * 0.85; return [cx + ring[j][0] * m * k, cx + ring[j][1] * m * k]; });
    g.lineCap = 'round';
    nodes.forEach((p, a) => { for (const [dist, b] of nodes.map((q, b) => [Math.hypot(q[0] - p[0], q[1] - p[1]), b]).filter(([, b]) => b !== a).sort((u, v) => u[0] - v[0]).slice(0, 1)) { if (dist > S * 0.13) continue; const q = nodes[b]; g.strokeStyle = `rgba(10,10,11,${0.5 + Math.random() * 0.4})`; g.lineWidth = 0.8 + Math.random() * 1.4; g.beginPath(); g.moveTo(p[0], p[1]); g.quadraticCurveTo((p[0] + q[0]) / 2 + (Math.random() - 0.5) * 14, (p[1] + q[1]) / 2 + (Math.random() - 0.5) * 14, q[0], q[1]); g.stroke(); } });
    g.save(); g.filter = 'blur(9px)'; blob(1.22); g.fillStyle = 'rgba(24,23,22,0.55)'; g.fill(); g.restore();
    for (let s = 0; s < 800; s++) { const j = Math.random() * N | 0, m = 0.98 + Math.random() * Math.random() * 0.42, r = 1.2 + Math.random() * 3.4, v = 70 + Math.random() * 75; g.fillStyle = `rgba(${v + 14 | 0},${v + 6 | 0},${v - 10 | 0},${0.55 + Math.random() * 0.45})`; g.beginPath(); g.ellipse(cx + ring[j][0] * m * k + (Math.random() - 0.5) * 9, cx + ring[j][1] * m * k + (Math.random() - 0.5) * 9, r, r * 0.6, Math.random() * 3, 0, 6.283); g.fill(); }
    g.globalCompositeOperation = 'destination-out'; blob(0.99); g.fill(); g.globalCompositeOperation = 'source-over';
    blob(1); g.strokeStyle = 'rgba(8,8,8,0.8)'; g.lineWidth = 2; g.stroke();
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(plane, plane), new THREE.MeshStandardMaterial(decal({ map: colorTex(c), roughness: 1, envMapIntensity: 0.2, polygonOffsetFactor: -4 })));
    mesh.rotation.x = -Math.PI / 2; mesh.position.y = 0.012; mesh.receiveShadow = true; mesh.renderOrder = 2;
    const group = new THREE.Group(); group.add(bowl, mesh);
    for (let s = 0; s < 9; s++) { const j = rnd() * N | 0, m = range(1.05, 1.7), st = new THREE.Mesh(stoneGeo, stoneMat), r = range(0.02, 0.05); st.scale.set(r, r * 0.6, r * range(0.7, 1.3)); st.position.set(ring[j][0] * m, r * 0.4, ring[j][1] * m); st.rotation.y = rnd() * 3; st.castShadow = true; group.add(st); }
    // selection frame: corner brackets in the severity colour, faint until hovered or selected
    const hx = size * 0.72 * Math.max(1, stretch), q = hx * 0.3, pts = [];
    for (const [sx, sz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) pts.push(sx * hx, 0, sz * (hx - q), sx * hx, 0, sz * hx, sx * hx, 0, sz * hx, sx * (hx - q), 0, sz * hx);
    const fg = new THREE.BufferGeometry(); fg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const frame = new THREE.LineSegments(fg, new THREE.LineBasicMaterial({ color: SEVERITY[severity], transparent: true, opacity: 0.3 })); frame.position.y = 0.03; group.add(frame);
    const og = new THREE.BufferGeometry(); og.setAttribute('position', new THREE.Float32BufferAttribute(ring.flatMap(([dx, dz]) => [dx * 1.2, 0, dz * 1.2]), 3));
    const outline = new THREE.LineLoop(og, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 })); outline.position.y = 0.035; outline.visible = false; group.add(outline);
    const halo = new THREE.Mesh(new THREE.PlaneGeometry(size * 3.4, size * 3.4), lightMat(SEVERITY[severity])); halo.rotation.x = -Math.PI / 2; halo.position.y = 0.045; halo.renderOrder = 4; halo.visible = false; group.add(halo);
    world.add(group);
    return { group, mesh, frame, outline, halo, glow: 0, severity, size, depth, x, z0, id: `DEMO-P${String(i + 1).padStart(2, '0')}` };
  });
  holeUniform.value = new THREE.CanvasTexture(holeCanvas); holeUniform.value.wrapT = THREE.RepeatWrapping; holeUniform.value.minFilter = THREE.LinearFilter; holeUniform.value.generateMipmaps = false;

  // ------------------------------------------------------------------ animation and interaction
  const wrap = (z, camZ) => camZ + BEHIND + ((((z - camZ - BEHIND) % WINDOW) - WINDOW) % WINDOW); // 290 m ahead .. 30 m behind
  const CONDITION = { Low: 'Surface breaking up', Medium: 'Open pothole', High: 'Deep pothole, base exposed', Critical: 'Severe failure in the wheel path' };
  // flow: 1 = traffic and camera moving, 0 = held still while a pothole is inspected; it eases between the two
  let active = null, pinned = false, closeTimer = 0, camLocalZ = 0, flow = 1, flowTarget = 1, dirty = true, parX = 0, parTarget = 0;

  // Day and night: one value, 0 = day and 1 = night, eased when the mode changes. The same scene is relit.
  let night = 0, nightTarget = 0;
  headMat.emissive.set(0xfff1d0); headMat.emissiveIntensity = 0;
  const NIGHT_FOG = new THREE.Color(0x0b111c), NIGHT_SUN = new THREE.Color(0x9fb4d8), DAY_SUN = sun.color.clone(), dayFog = scene.fog.color.clone();
  const dome = new THREE.Mesh(new THREE.SphereGeometry(900, 24, 12), new THREE.MeshBasicMaterial({ color: 0x060a13, side: THREE.BackSide, transparent: true, opacity: 0, depthWrite: false, fog: false }));
  dome.visible = false; scene.add(dome); // darkens the photographed sky
  function applyNight() {
    const n = night, lit = n > 0.01;
    sun.intensity = lerp(3.9, 0.4, n); sun.color.copy(DAY_SUN).lerp(NIGHT_SUN, n); hemi.intensity = lerp(1.15, 0.34, n);
    scene.fog.color.copy(dayFog).lerp(NIGHT_FOG, n);
    dome.material.opacity = n * 0.96; dome.visible = lit;
    for (const m of reflective) m.envMapIntensity = m.userData.env * (1 - 0.88 * n);
    for (const m of facadeMats) m.emissiveIntensity = n * 0.95;
    for (const m of officeMats) m.emissiveIntensity = n * 0.7;
    for (const m of shopMats) m.emissiveIntensity = n * 0.38;
    lensMat.emissiveIntensity = n * 3.2; headMat.emissiveIntensity = n * 2.8; tailMat.emissiveIntensity = 0.35 + n * 2.0;
    lampPoolMat.opacity = n * 0.55; beamMat.opacity = n * 0.5;
    for (const m of lights) m.visible = lit;
    for (const p of potholes) { p.halo.material.opacity = n * 0.42; p.halo.visible = lit; }
    dirty = true;
  }
  function setNight(on) { nightTarget = on ? 1 : 0; if (reduce || !raf) { night = nightTarget; applyNight(); update(time); } }
  const card = document.getElementById('roadSceneCard'), tmp = new V3(), el = (id) => document.getElementById(id);
  // every vehicle drifts a little around its lane speed, far less than the gap to the next one, and bikes weave slightly
  for (const c of cars) { c.amp = 1.2 + rnd() * 1.6; c.rate = 0.25 + rnd() * 0.3; c.phase = rnd() * 6.28; c.sway = c.obj.wheels.length === 2 ? 0.28 : 0.05; }

  function update(t) {
    const camZ = -t * CAM_SPEED, mid = camZ - ROAD_LEN / 2 + 55; camLocalZ = camZ + CAM.back;
    camera.position.copy(world.localToWorld(tmp.set(CAM.x + parX, CAM.y, camLocalZ))); camera.lookAt(world.localToWorld(tmp.set(CAM.lookX + parX * 0.35, 0.5, camZ - CAM.ahead)));
    dome.position.copy(camera.position);
    for (const f of followers) f.position.z = mid;
    for (const a of anchored) a.t.offset.y = -a.mesh.position.z / a.period;
    sun.target.position.copy(world.localToWorld(tmp.set(0, 0, camZ - 34))); sun.position.copy(sun.target.position).addScaledVector(sunDir, 150);
    for (const s of scenery) s.obj.position.set(s.x, 0, wrap(-s.z0, camZ));
    const first = Math.ceil((camZ - (WINDOW - BEHIND)) / 2.2) * 2.2;
    for (let i = 0; i < SHRUBS; i++) { const z = first + i * 2.2, r = h2(Math.round(z / 2.2), 3); dummy.position.set((r - 0.5) * 0.3, 0.28, z); dummy.rotation.set(0, r * 6.28, 0); dummy.scale.setScalar(0.6 + r * 0.35); dummy.updateMatrix(); shrubs.setMatrixAt(i, dummy.matrix); }
    shrubs.instanceMatrix.needsUpdate = true;
    for (const c of cars) {
      const along = c.lane.speed * t + c.amp * Math.sin(t * c.rate + c.phase);
      c.obj.position.set(c.lane.x + c.sway * Math.sin(t * 0.7 + c.phase), 0, wrap(c.z0 + c.lane.dir * along, camZ));
      const far = night < 0.5 && c.obj.position.z < camZ - (LOW ? 70 : 120); // lamps stay on in the distance at night if (c.far !== far) { c.far = far; for (const d of c.obj.detail || []) d.visible = !far; }
      const spin = along / WHEEL_R; for (const w of c.obj.wheels) w.rotation.x = spin;
    }
    for (const p of potholes) {
      p.group.position.set(p.x, 0, wrap(p.z0, camZ));
      p.glow += ((p === active ? 1 : 0) - p.glow) * (raf ? 0.2 : 1);
      p.frame.material.opacity = Math.min(1, 0.3 + 0.45 * night + 0.7 * p.glow);
      p.outline.material.color.set(p.glow > 0.5 ? 0xffffff : SEVERITY[p.severity]); p.outline.material.opacity = Math.max(0.85 * p.glow, 0.7 * night); p.outline.visible = p.glow > 0.01 || night > 0.01;
    }
    renderer.render(scene, camera);
  }

  // Put the panel beside the pothole, away from the navigation, the headline block and the tag line.
  function placeCard() {
    const v = active.group.getWorldPosition(tmp).project(camera), W = host.clientWidth, H = host.clientHeight, hr = host.getBoundingClientRect();
    const x = (v.x * 0.5 + 0.5) * W, y = (-v.y * 0.5 + 0.5) * H, cw = card.offsetWidth || 260, ch = card.offsetHeight || 240;
    const avoid = [...host.parentElement.querySelectorAll('[data-scene-avoid]')].map((e) => { const r = e.getBoundingClientRect(); return [r.left - hr.left - 8, r.top - hr.top - 8, r.right - hr.left + 8, r.bottom - hr.top + 8]; });
    const keep = ([l, t]) => [clamp(l, 10, Math.max(10, W - cw - 10)), clamp(t, 104, Math.max(104, H - ch - 12))];
    const overlap = ([l, t]) => avoid.reduce((n, r) => n + Math.max(0, Math.min(l + cw, r[2]) - Math.max(l, r[0])) * Math.max(0, Math.min(t + ch, r[3]) - Math.max(t, r[1])), 0) + (l < x && x < l + cw && t < y && y < t + ch ? 1e7 : 0);
    const options = (W < 560 ? [[(W - cw) / 2, 104], [(W - cw) / 2, y + 40]] : [[x + 28, y - ch / 2], [x - cw - 28, y - ch / 2], [x - cw / 2, y - ch - 28], [x - cw / 2, y + 34]]).map(keep);
    const best = options.sort((m, n) => overlap(m) - overlap(n))[0];
    card.style.left = best[0] + 'px'; card.style.top = best[1] + 'px';
  }
  function show(p, pin) {
    clearTimeout(closeTimer); if (pin) pinned = true;
    if (active === p) return;
    active = p; flowTarget = 0; dirty = true;
    el('roadSceneCardTitle').textContent = `Pothole ${p.id}`;
    const sev = el('roadSceneCardSev'); sev.textContent = p.severity; sev.style.background = SEVERITY[p.severity];
    el('roadSceneCardSize').textContent = `about ${p.size.toFixed(1)} m across`;
    el('roadSceneCardDepth').textContent = `about ${Math.round(p.depth * 100)} cm`;
    el('roadSceneCardCond').textContent = CONDITION[p.severity];
    placeCard(); card.dataset.open = 'true'; host.style.cursor = 'pointer';
    if (!raf) update(time);
  }
  function hide() {
    clearTimeout(closeTimer); if (!active) return;
    active = null; pinned = false; flowTarget = 1; dirty = true; delete card.dataset.open; host.style.cursor = 'default';
    if (!raf) update(time);
  }
  const hideSoon = () => { if (pinned) return; clearTimeout(closeTimer); closeTimer = setTimeout(hide, 260); }; // time to reach the panel

  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  const pick = (e) => {
    const r = host.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(potholes.map((p) => p.mesh))[0];
    return hit ? potholes.find((p) => p.mesh === hit.object) : null;
  };
  // while the scene eases to a stop the pothole still drifts a little: stay selected while the pointer is close to it
  const nearActive = (e) => { const v = active.group.getWorldPosition(tmp).project(camera), r = host.getBoundingClientRect(); return Math.hypot(r.left + (v.x * 0.5 + 0.5) * r.width - e.clientX, r.top + (-v.y * 0.5 + 0.5) * r.height - e.clientY) < 70; };
  const onMove = (e) => {
    if (disposed || e.pointerType !== 'mouse') return;
    parTarget = reduce ? 0 : (e.clientX / innerWidth - 0.5) * 1.0;
    const p = pick(e);
    if (p && (!pinned || p === active)) show(p, false);
    else if (active && !pinned) { if (nearActive(e)) clearTimeout(closeTimer); else hideSoon(); }
    host.style.cursor = p ? 'pointer' : 'default';
  };
  const onLeave = () => { parTarget = 0; if (!pinned) hideSoon(); };
  const onClick = (e) => { if (disposed) return; const p = pick(e); if (p) { if (active !== p) hide(); show(p, true); } else hide(); };
  const onKey = (e) => { if (e.key === 'Escape') hide(); };
  const onCardEnter = () => clearTimeout(closeTimer), onCardLeave = () => { if (!pinned) hideSoon(); };
  host.addEventListener('pointermove', onMove); host.addEventListener('pointerleave', onLeave); host.addEventListener('click', onClick);
  card.addEventListener('pointerenter', onCardEnter); card.addEventListener('pointerleave', onCardLeave);
  document.addEventListener('keydown', onKey);
  el('roadSceneCardClose').onclick = hide;

  function fit(w, h) { if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w / h < 0.8 ? 62 : 44; camera.updateProjectionMatrix(); }
  let time = 20, last = performance.now(), raf = 0, visible = true, fps = 0, fpsFrames = 0, fpsSince = last, seconds = 0, slow = 0, quality = LOW ? 1 : 2;
  fit(host.clientWidth, host.clientHeight);
  const ro = new ResizeObserver(() => { fit(host.clientWidth, host.clientHeight); if (!raf) update(time); });
  ro.observe(host);

  // Adaptive quality: three seconds below 28 fps step it down (sharpness and shadow size first, shadows last).
  function lowerQuality() {
    quality--;
    if (quality === 1) { renderer.setPixelRatio(1); fit(host.clientWidth, host.clientHeight); sun.shadow.mapSize.setScalar(2048); if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; } }
    else if (quality === 0) sun.castShadow = false;
  }
  function loop(now) { raf = requestAnimationFrame(loop); step(now); }
  function step(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    flow += (flowTarget - flow) * (1 - Math.exp(-dt * 7)); if (Math.abs(flowTarget - flow) < 0.01) flow = flowTarget;
    parX += (parTarget - parX) * (1 - Math.exp(-dt * 2.5));
    if (night !== nightTarget) { night += (nightTarget - night) * (1 - Math.exp(-dt * 2.6)); if (Math.abs(nightTarget - night) < 0.004) night = nightTarget; applyNight(); }
    const settling = potholes.some((p) => Math.abs((p === active ? 1 : 0) - p.glow) > 0.01) || Math.abs(parTarget - parX) > 0.004;
    if (flow > 0 || settling || dirty) { time += dt * flow; update(time); dirty = false; }
    fpsFrames++;
    if (now - fpsSince >= 1000) {
      fps = Math.round((fpsFrames * 1000) / (now - fpsSince)); fpsFrames = 0; fpsSince = now;
      // below 8 fps the browser is throttling the page (background or hidden), which says nothing about the device
      if (++seconds > 2 && quality > 0 && fps >= 8 && flow === 1) { if (fps < 28) { if (++slow >= 3) { slow = 0; lowerQuality(); } } else slow = 0; }
    }
  }
  const start = () => { if (!raf && !reduce && visible && !document.hidden && !disposed) { last = fpsSince = performance.now(); fpsFrames = 0; raf = requestAnimationFrame(loop); } };
  const stop = () => { if (raf) cancelAnimationFrame(raf); raf = 0; };
  const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start(); else stop(); }, { threshold: 0.05 });
  io.observe(host);
  const onVisibility = () => { if (document.hidden) stop(); else start(); };
  document.addEventListener('visibilitychange', onVisibility);
  update(time); start();

  return {
    setNight,
    stats: () => ({ fps, quality, night: +night.toFixed(3), flow: +flow.toFixed(3), time: +time.toFixed(3), active: active ? active.id : null, pinned, running: !!raf, calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, pixelRatio: renderer.getPixelRatio(), width: host.clientWidth, height: host.clientHeight }),
    // average milliseconds to draw one frame, finished on the GPU; independent of how often the browser schedules frames (used by tests)
    bench: (n = 60) => { const gl = renderer.getContext(), t0 = performance.now(); for (let i = 0; i < n; i++) { update(time + i * 0.016); gl.finish(); } return (performance.now() - t0) / n; },
    internals: { renderer, scene, camera, sun, world, update: (t) => update(t ?? time), advance: (ms) => step(last + ms) }, // advance: one animation step, for tests in browsers that hold frames back
    // keyboard access: select the nearest pothole in view and keep it open
    selectNearest: () => { const list = potholes.filter((p) => p.group.position.z < camLocalZ - 22 && p.group.position.z > camLocalZ - 90).sort((m, n) => n.group.position.z - m.group.position.z); if (!list.length) return false; hide(); show(list[0], true); return true; },
    close: hide,
    // screen positions of the potholes ahead of the camera (used by tests)
    potholes: () => potholes.filter((p) => p.group.position.z < camLocalZ - 18).map((p) => { const v = p.group.getWorldPosition(new V3()).project(camera), r = host.getBoundingClientRect(); return { id: p.id, severity: p.severity, x: r.left + (v.x * 0.5 + 0.5) * r.width, y: r.top + (-v.y * 0.5 + 0.5) * r.height }; }).filter((p) => p.x > 0 && p.y > 0 && p.x < innerWidth && p.y < innerHeight),
    dispose() {
      disposed = true; stop(); io.disconnect(); ro.disconnect(); document.removeEventListener('visibilitychange', onVisibility); document.removeEventListener('keydown', onKey); hide(); clearTimeout(closeTimer);
      host.removeEventListener('pointermove', onMove); host.removeEventListener('pointerleave', onLeave); host.removeEventListener('click', onClick); card.removeEventListener('pointerenter', onCardEnter); card.removeEventListener('pointerleave', onCardLeave);
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); for (const m of [].concat(o.material || [])) { for (const k in m) if (m[k] && m[k].isTexture) m[k].dispose(); m.dispose(); } });
      if (holeUniform.value) holeUniform.value.dispose();
      if (envTex) envTex.dispose();
      if (scene.background && scene.background.isTexture) scene.background.dispose();
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    },
  };
}
