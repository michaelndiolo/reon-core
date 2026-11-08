// REON twin: a 3D copy of a store's 250-cell string and the store it powers. Click a cell to fail it; Python (GR.analyse) decides what happens, this file only draws it.
// Runs as a Streamlit v2 component; THREE (r160 UMD) is prepended to this file by hackkit/reon_twin_ui.py.
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector("#reon-twin");
  if (!root) return;
  let S = root.__twin;
  if (!S || !S.alive()) S = root.__twin = build(root);
  S.pick = (v) => setTriggerValue("pick", v);
  S.update(data);
}

function build(root) {
  const THREE = globalThis.THREE;
  const NC = 25, NR = 10, SX = 1.05, SZ = 1.2, HS = 2.6, TOP = 0.15;
  const H = 580;
  root.style.height = H + "px";
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch (e) {
    root.innerHTML = '<div style="padding:32px;color:#c8dcf2;font:18px Figtree,Arial,sans-serif">The 3D view needs WebGL. Open this page in a browser with WebGL on.</div>';
    return { alive: () => true, update() {}, pick() {} };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(root.clientWidth || 900, H);
  const canvas = renderer.domElement;
  canvas.style.display = "block";
  root.appendChild(canvas);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x07121f);
  scene.fog = new THREE.Fog(0x07121f, 55, 110);
  const camera = new THREE.PerspectiveCamera(38, (root.clientWidth || 900) / H, 0.1, 300);
  const target = new THREE.Vector3(6.5, 0.8, 1.6);
  let theta = 0.3, phi = 0.98, radius = 39, idle = 0, auto = true;
  function placeCamera() {
    camera.position.set(target.x + radius * Math.sin(phi) * Math.sin(theta), target.y + radius * Math.cos(phi), target.z + radius * Math.sin(phi) * Math.cos(theta));
    camera.lookAt(target);
  }
  placeCamera();

  scene.add(new THREE.AmbientLight(0x8fb2d8, 0.75));
  const sun = new THREE.DirectionalLight(0xbcd4f0, 0.9);
  sun.position.set(-14, 26, 18);
  scene.add(sun);

  // ground and plinth
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(160, 100), new THREE.MeshStandardMaterial({ color: 0x0b1c30, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
  const grid = new THREE.GridHelper(120, 60, 0x1d3a5c, 0x12263b);
  grid.position.y = 0.01;
  scene.add(grid);
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(NC * SX + 1.6, 0.3, NR * SZ + 1.4), new THREE.MeshStandardMaterial({ color: 0x10263d, roughness: 0.8 }));
  plinth.position.y = -0.14;
  scene.add(plinth);

  // cells
  const N = NC * NR;
  const cellPos = (i) => {
    const r = Math.floor(i / NC), k = i % NC, c = r % 2 === 0 ? k : NC - 1 - k;
    return new THREE.Vector3((c - (NC - 1) / 2) * SX, 0, (r - (NR - 1) / 2) * SZ);
  };
  const pos = [];
  for (let i = 0; i < N; i++) pos.push(cellPos(i));
  const cellMesh = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.38, 0.38, 1, 20), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.42, metalness: 0.3 }), N);
  cellMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  cellMesh.frustumCulled = false;
  scene.add(cellMesh);

  // store
  const store = new THREE.Group();
  store.position.set(21.5, 0, 0);
  scene.add(store);
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0x1c3b5e, roughness: 0.8 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(7, 4.6, 6), bodyMat);
  body.position.y = 2.3;
  store.add(body);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(7.6, 0.5, 6.6), new THREE.MeshStandardMaterial({ color: 0x2f5fa3, roughness: 0.6 }));
  roof.position.y = 4.85;
  store.add(roof);
  const winMat = new THREE.MeshStandardMaterial({ color: 0x0a1626, emissive: 0xffc857, emissiveIntensity: 0, roughness: 0.4 });
  [[-1.9, 2.5], [1.9, 2.5]].forEach(([x, y]) => {
    const w = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.6, 0.12), winMat);
    w.position.set(x, y, 3.04);
    store.add(w);
  });
  const door = new THREE.Mesh(new THREE.BoxGeometry(1.3, 2.5, 0.12), winMat);
  door.position.set(0, 1.25, 3.05);
  store.add(door);
  const sc = document.createElement("canvas");
  sc.width = 512; sc.height = 96;
  const sx = sc.getContext("2d");
  sx.fillStyle = "#2f5fa3"; sx.fillRect(0, 0, 512, 96);
  sx.fillStyle = "#ffffff"; sx.font = "700 54px Arial"; sx.textAlign = "center"; sx.textBaseline = "middle";
  sx.fillText("24/7  MARKET", 256, 50);
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(6.2, 1.16), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(sc) }));
  sign.position.set(0, 4.15, 3.03);
  store.add(sign);
  const storeLight = new THREE.PointLight(0xffc857, 0, 22, 1.6);
  storeLight.position.set(21.5, 3, 6);
  scene.add(storeLight);

  // glow sprites for failed cells
  const gc = document.createElement("canvas");
  gc.width = gc.height = 128;
  const gx = gc.getContext("2d");
  const grad = gx.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, "rgba(255,110,80,0.95)"); grad.addColorStop(0.4, "rgba(224,87,58,0.45)"); grad.addColorStop(1, "rgba(224,87,58,0)");
  gx.fillStyle = grad; gx.fillRect(0, 0, 128, 128);
  const glowTex = new THREE.CanvasTexture(gc);

  // dynamic groups
  const dyn = new THREE.Group();
  scene.add(dyn);
  const levelMat = new THREE.MeshBasicMaterial({ color: 0xffc857, transparent: true, opacity: 0.13, side: THREE.DoubleSide, depthWrite: false });
  const level = new THREE.Mesh(new THREE.PlaneGeometry(NC * SX + 1, NR * SZ + 0.4), levelMat);
  level.rotation.x = -Math.PI / 2;
  scene.add(level);
  const levelEdge = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-1, 0, -1), new THREE.Vector3(1, 0, -1), new THREE.Vector3(1, 0, 1), new THREE.Vector3(-1, 0, 1)]), new THREE.LineBasicMaterial({ color: 0xffc857 }));
  levelEdge.scale.set((NC * SX + 1) / 2, 1, (NR * SZ + 0.4) / 2);
  scene.add(levelEdge);
  const hover = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 16), new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.8 }));
  hover.visible = false;
  scene.add(hover);

  // rain
  const RN = 420;
  const rainGeo = new THREE.BufferGeometry();
  const rp = new Float32Array(RN * 3);
  for (let i = 0; i < RN; i++) { rp[i * 3] = (Math.random() - 0.5) * 90; rp[i * 3 + 1] = Math.random() * 30; rp[i * 3 + 2] = (Math.random() - 0.5) * 50; }
  rainGeo.setAttribute("position", new THREE.BufferAttribute(rp, 3));
  const rain = new THREE.Points(rainGeo, new THREE.PointsMaterial({ color: 0x7fa6d6, size: 0.12, transparent: true, opacity: 0.55 }));
  scene.add(rain);

  // overlay
  root.style.position = "relative";
  const ov = document.createElement("div");
  ov.style.cssText = "position:absolute;inset:0;pointer-events:none;font-family:Figtree,Arial,sans-serif;color:#fff";
  ov.innerHTML = '<div id="tw-modes" style="position:absolute;left:16px;top:16px;display:flex;gap:8px;pointer-events:auto"></div>' +
    '<div id="tw-card" style="position:absolute;right:16px;top:16px;width:300px;background:rgba(15,37,57,0.88);border:1px solid #2b4a6e;border-radius:16px;padding:14px 18px"></div>' +
    '<div id="tw-hint" style="position:absolute;left:16px;bottom:14px;font-size:14px;color:#9fc0e8">Click a cell to fail it. Drag to turn, scroll to zoom. Shorter cells are weaker.</div>' +
    '<div id="tw-tip" style="position:absolute;display:none;background:rgba(7,18,31,0.95);border:1px solid #3a6194;border-radius:10px;padding:6px 10px;font-size:14px;white-space:nowrap"></div>';
  root.appendChild(ov);
  const $ = (id) => ov.querySelector("#" + id);
  let mode = "control";
  const modes = $("tw-modes");
  [["plain", "Plain string"], ["control", "With cell-level control"]].forEach(([k, label]) => {
    const b = document.createElement("button");
    b.textContent = label; b.dataset.k = k;
    b.style.cssText = "cursor:pointer;border-radius:999px;padding:8px 16px;font:600 14px Figtree,Arial,sans-serif;border:1px solid #3a6194;color:#fff;background:rgba(15,37,57,0.88)";
    b.onclick = () => { mode = k; draw(); };
    modes.appendChild(b);
  });

  let D = null, particles = null, pathCurve = null, alive = true;
  const failedGlows = [];
  const labels = [];
  const tmpM = new THREE.Matrix4(), tmpC = new THREE.Color();
  const cHealthy = new THREE.Color(0x4c86d6), cWeak = new THREE.Color(0xffc857), cFail = new THREE.Color(0xe0573a);
  const heightOf = (i) => D.health[i] * HS;
  const BUS = HS + 0.45;
  const top = (i) => new THREE.Vector3(pos[i].x, BUS, pos[i].z);

  function clearDyn() {
    while (dyn.children.length) {
      const o = dyn.children.pop();
      if (o.geometry) o.geometry.dispose();
    }
    failedGlows.length = 0;
    while (labels.length) labels.pop().el.remove();
  }
  function lineOf(pts, color, opacity, width) {
    if (pts.length < 2) return null;
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
    dyn.add(l);
    return l;
  }
  function arc(a, b) {
    const mid = a.clone().add(b).multiplyScalar(0.5);
    mid.y += 1.5;
    return new THREE.QuadraticBezierCurve3(a, mid, b).getPoints(14);
  }

  function draw() {
    if (!D) return;
    clearDyn();
    const failed = new Set(D.failed);
    const early = new Set(mode === "control" ? D.early : []);
    // cells
    for (let i = 0; i < N; i++) {
      const h = heightOf(i);
      tmpM.makeScale(1, h, 1);
      tmpM.setPosition(pos[i].x, h / 2, pos[i].z);
      cellMesh.setMatrixAt(i, tmpM);
      if (failed.has(i)) tmpC.copy(cFail);
      else {
        const t = Math.min(1, Math.max(0, (D.health[i] - 0.72) / 0.18));
        tmpC.copy(cWeak).lerp(cHealthy, t);
        if (early.has(i)) tmpC.lerp(new THREE.Color(0xffffff), 0.4);
      }
      cellMesh.setColorAt(i, tmpC);
    }
    cellMesh.instanceMatrix.needsUpdate = true;
    cellMesh.computeBoundingSphere();
    cellMesh.instanceColor.needsUpdate = true;
    // glows
    D.failed.forEach((i) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      s.position.set(pos[i].x, heightOf(i) + 0.8, pos[i].z);
      s.scale.set(3.4, 3.4, 1);
      dyn.add(s);
      failedGlows.push(s);
      if (labels.length < 6) {
        const el = document.createElement('div');
        el.style.cssText = 'position:absolute;transform:translate(-50%,-100%);background:#e0573a;color:#fff;font:700 13px Figtree,Arial,sans-serif;padding:3px 9px;border-radius:999px;white-space:nowrap';
        el.textContent = 'Cell ' + (i + 1) + ' open';
        ov.appendChild(el);
        labels.push({ el, p: new THREE.Vector3(pos[i].x, heightOf(i) + 1.9, pos[i].z) });
      }
    });
    // series path (cell tops, then a cable to the store along the front edge)
    const endCell = top(N - 1);
    const cable = [new THREE.Vector3(endCell.x, BUS, endCell.z), new THREE.Vector3(endCell.x, 0.5, endCell.z + 0.6), new THREE.Vector3(endCell.x, 0.5, 8.4), new THREE.Vector3(21.5, 0.5, 8.4), new THREE.Vector3(21.5, 0.5, 3.4)];
    let active = [], dead = [], lit = false;
    if (D.refused) {
      for (let i = 0; i < N; i++) dead.push(top(i));
      dead = dead.concat(cable);
    } else if (mode === "plain") {
      const first = D.failed.length ? Math.min(...D.failed) : N;
      for (let i = 0; i < N; i++) (i < first ? active : dead).push(top(i));
      if (first < N) { active.push(top(first)); }
      if (first === N) active = active.concat(cable); else dead = dead.concat(cable);
      lit = D.plain_kwh > 0;
    } else {
      let prev = null, pendingFail = false;
      for (let i = 0; i < N; i++) {
        if (failed.has(i)) { pendingFail = true; continue; }
        const t = top(i);
        if (pendingFail && prev) arc(prev, t).forEach((p) => active.push(p));
        active.push(t);
        prev = t; pendingFail = false;
      }
      active = active.concat(cable);
      lit = D.ours_kwh > 0;
    }
    lineOf(dead, 0x3a4f6b, 0.7);
    lineOf(active, 0xffc857, 0.95);
    // flowing current
    if (particles) { scene.remove(particles); particles.geometry.dispose(); particles = null; }
    pathCurve = active.length > 1 ? new THREE.CatmullRomCurve3(active, false, "centripetal", 0.0) : null;
    if (pathCurve) {
      const PN = 120;
      const pg = new THREE.BufferGeometry();
      pg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(PN * 3), 3));
      particles = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xffe08a, size: 0.42, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }));
      particles.userData.n = PN;
      scene.add(particles);
    }
    // usable level plane
    const lv = mode === "plain" ? D.line_plain : D.line_ours;
    if (lv > 0 && !D.refused) {
      level.visible = true; levelEdge.visible = true; levelEdge.position.set(0, lv * HS + 0.03, 0); levelEdge.material.color.set(mode === "plain" ? 0xe0573a : 0xffc857);
      level.position.set(0, lv * HS + 0.02, 0);
      levelMat.color.set(mode === "plain" ? 0xe0573a : 0xffc857);
    } else { level.visible = false; levelEdge.visible = false; }
    // store
    winMat.emissiveIntensity = lit ? 1.15 : 0;
    storeLight.intensity = lit ? 2.2 : 0;
    winMat.color.set(lit ? 0x6b5a2a : 0x0a1626);
    // buttons + card
    modes.querySelectorAll("button").forEach((b) => {
      const on = b.dataset.k === mode;
      b.style.background = on ? "#ffc857" : "rgba(15,37,57,0.88)";
      b.style.color = on ? "#17324f" : "#fff";
    });
    const card = $("tw-card");
    const kwh = mode === "plain" ? D.plain_kwh : D.ours_kwh, hrs = mode === "plain" ? D.plain_h : D.ours_h;
    const title = mode === "plain" ? "Plain string" : "With cell-level control";
    let line1, line2;
    if (D.refused) { line1 = "String offline"; line2 = "One failure too many for the inverter's minimum voltage. The hardware opens the string."; }
    else if (kwh <= 0) { line1 = "Lights out"; line2 = "A plain string with one open cell delivers nothing, and a balancer cannot move charge through it."; }
    else { line1 = hrs.toFixed(1) + " h of backup"; line2 = kwh.toFixed(0) + " kWh at " + D.load_kw.toFixed(0) + " kW. " + (mode === "plain" ? "Capped by the weakest cell (the red plane)." : "The amber plane is higher: the weakest cells may leave early."); }
    card.innerHTML = '<div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#ffc857;font-weight:700">' + title + '</div>' +
      '<div style="font-size:34px;font-weight:700;line-height:1.1;margin:6px 0 4px;color:' + (kwh > 0 && !D.refused ? "#ffffff" : "#ff8a6b") + '">' + line1 + '</div>' +
      '<div style="font-size:15px;line-height:1.35;color:#c8dcf2">' + line2 + '</div>';
  }

  // interaction
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  function pickAt(ev) {
    const r = canvas.getBoundingClientRect();
    mouse.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObject(cellMesh)[0];
    return hit ? hit.instanceId : null;
  }
  let down = null, drag = false;
  canvas.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; drag = false; canvas.setPointerCapture(e.pointerId); idle = 0; auto = false; });
  canvas.addEventListener("pointermove", (e) => {
    if (down) {
      const dx = e.clientX - down.x, dy = e.clientY - down.y;
      if (Math.abs(dx) + Math.abs(dy) > 5) drag = true;
      if (drag) { theta -= dx * 0.006; phi = Math.min(1.45, Math.max(0.35, phi - dy * 0.006)); down = { x: e.clientX, y: e.clientY }; placeCamera(); }
      return;
    }
    const i = pickAt(e), tip = $("tw-tip");
    if (i === null || !D) { hover.visible = false; tip.style.display = "none"; canvas.style.cursor = "grab"; return; }
    canvas.style.cursor = "pointer";
    const h = heightOf(i);
    hover.visible = true; hover.scale.set(1, h + 0.3, 1); hover.position.set(pos[i].x, (h + 0.3) / 2, pos[i].z);
    const failed = D.failed.indexOf(i) >= 0, early = D.early.indexOf(i) >= 0;
    tip.innerHTML = "Cell " + (i + 1) + " of " + N + " · health " + Math.round(D.health[i] * 100) + "%" + (failed ? " · <b style='color:#ff8a6b'>open (click to repair)</b>" : early ? " · may leave early" : " · click to fail it");
    const r = canvas.getBoundingClientRect();
    tip.style.display = "block"; tip.style.left = Math.min(e.clientX - r.left + 14, r.width - 260) + "px"; tip.style.top = (e.clientY - r.top + 14) + "px";
  });
  canvas.addEventListener("pointerup", (e) => {
    const was = down; down = null;
    if (drag || !was) return;
    const i = pickAt(e), api = root.__twin;
    if (i !== null && api && api.pick) api.pick({ cell: i, t: Date.now() });
  });
  canvas.addEventListener("pointerleave", () => { $("tw-tip").style.display = "none"; hover.visible = false; });
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); radius = Math.min(62, Math.max(18, radius * (e.deltaY > 0 ? 1.07 : 0.93))); idle = 0; auto = false; placeCamera(); }, { passive: false });
  new ResizeObserver(() => { const w = root.clientWidth || 900; renderer.setSize(w, H); camera.aspect = w / H; camera.updateProjectionMatrix(); }).observe(root);

  // loop
  const clock = new THREE.Clock();
  let tAcc = 0;
  function loop() {
    if (!root.isConnected) { alive = false; renderer.dispose(); return; }
    requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.05);
    tAcc += dt;
    idle += dt;
    if (!auto && idle > 8) auto = true;
    if (auto) { theta += dt * 0.05; placeCamera(); }
    const rpa = rainGeo.attributes.position;
    for (let i = 0; i < RN; i++) { let y = rpa.array[i * 3 + 1] - dt * 20; if (y < 0) y += 30; rpa.array[i * 3 + 1] = y; rpa.array[i * 3] -= dt * 2; if (rpa.array[i * 3] < -45) rpa.array[i * 3] += 90; }
    rpa.needsUpdate = true;
    if (particles && pathCurve) {
      const n = particles.userData.n, arr = particles.geometry.attributes.position.array, v = new THREE.Vector3();
      for (let k = 0; k < n; k++) { const u = ((k / n) + tAcc * 0.055) % 1; pathCurve.getPointAt(u, v); arr[k * 3] = v.x; arr[k * 3 + 1] = v.y + 0.05; arr[k * 3 + 2] = v.z; }
      particles.geometry.attributes.position.needsUpdate = true;
    }
    failedGlows.forEach((s, j) => { const p = 0.78 + 0.22 * Math.sin(tAcc * 5 + j); s.scale.set(3.4 * p, 3.4 * p, 1); });
    labels.forEach((l) => { const v = l.p.clone().project(camera); const w = root.clientWidth || 900; l.el.style.left = ((v.x + 1) / 2) * w + 'px'; l.el.style.top = ((1 - v.y) / 2) * H + 'px'; });
    renderer.render(scene, camera);
  }
  loop();

  return {
    alive: () => alive,
    pick: null,
    update(d) { D = d; draw(); },
  };
}
