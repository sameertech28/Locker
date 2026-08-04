// Rotating vault door for the landing page hero (#vault-canvas).
(function () {
  const mount = document.getElementById("vault-canvas");
  if (!mount || typeof THREE === "undefined") return;

  const width = mount.clientWidth || 420;
  const height = mount.clientHeight || 420;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.set(0, 0, 9);

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(width, height);
  mount.appendChild(renderer.domElement);

  const key = new THREE.PointLight(0x00f0ff, 3, 50);
  key.position.set(5, 4, 6);
  scene.add(key);
  const rim = new THREE.PointLight(0x8b5cf6, 2.4, 50);
  rim.position.set(-5, -3, -4);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0x222233, 1.2));

  // Vault body: a ringed torus door with an inner hex core.
  const group = new THREE.Group();

  const doorGeo = new THREE.TorusGeometry(2.6, 0.35, 24, 100);
  const doorMat = new THREE.MeshStandardMaterial({ color: 0x14141f, metalness: 0.85, roughness: 0.25, emissive: 0x0a0a1f });
  const door = new THREE.Mesh(doorGeo, doorMat);
  group.add(door);

  const ringGeo = new THREE.TorusGeometry(2.0, 0.05, 16, 100);
  const ringMat = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 1.4, metalness: 0.4, roughness: 0.2 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  group.add(ring);

  const coreGeo = new THREE.IcosahedronGeometry(1.15, 0);
  const coreMat = new THREE.MeshStandardMaterial({ color: 0x8b5cf6, emissive: 0x8b5cf6, emissiveIntensity: 0.9, metalness: 0.6, roughness: 0.15, wireframe: true });
  const core = new THREE.Mesh(coreGeo, coreMat);
  group.add(core);

  for (let i = 0; i < 8; i++) {
    const boltGeo = new THREE.SphereGeometry(0.08, 12, 12);
    const boltMat = new THREE.MeshStandardMaterial({ color: 0xff2d55, emissive: 0xff2d55, emissiveIntensity: 1 });
    const bolt = new THREE.Mesh(boltGeo, boltMat);
    const angle = (i / 8) * Math.PI * 2;
    bolt.position.set(Math.cos(angle) * 2.6, Math.sin(angle) * 2.6, 0);
    group.add(bolt);
  }

  scene.add(group);

  // Orbiting particles like digital stars.
  const starCount = 220;
  const starPositions = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    const r = 4 + Math.random() * 3;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.random() * Math.PI;
    starPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    starPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    starPositions[i * 3 + 2] = r * Math.cos(phi);
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const starMat = new THREE.PointsMaterial({ color: 0x00f0ff, size: 0.06, transparent: true, opacity: 0.8 });
  const stars = new THREE.Points(starGeo, starMat);
  scene.add(stars);

  let hover = false;
  mount.addEventListener("mouseenter", () => (hover = true));
  mount.addEventListener("mouseleave", () => (hover = false));

  let openT = 0;
  const isLoggedIn = mount.dataset.open === "true";

  function animate() {
    requestAnimationFrame(animate);
    group.rotation.y += hover ? 0.012 : 0.004;
    core.rotation.x += 0.01;
    core.rotation.y += 0.006;
    stars.rotation.y -= 0.0015;

    if (isLoggedIn && openT < 1) {
      openT += 0.01;
      door.scale.setScalar(1 + openT * 0.15);
      doorMat.emissiveIntensity = openT;
    }

    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener("resize", () => {
    const w = mount.clientWidth || 420;
    const h = mount.clientHeight || 420;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
})();
