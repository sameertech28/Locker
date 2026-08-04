// Ambient particle field for #bg-canvas. Degrades gracefully if THREE isn't loaded.
(function () {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas || typeof THREE === "undefined") return;

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 60;

  const COUNT = window.innerWidth < 700 ? 500 : 1400;
  const positions = new Float32Array(COUNT * 3);
  for (let i = 0; i < COUNT; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 260;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 260;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 260;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  const material = new THREE.PointsMaterial({
    color: 0x00f0ff,
    size: 0.9,
    transparent: true,
    opacity: 0.55,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  scene.add(points);

  let mouseX = 0, mouseY = 0;
  window.addEventListener("mousemove", (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // Exposed so other scripts (e.g. upload success) can trigger a shockwave pulse.
  window.lockerPulse = function () {
    material.color.setHex(0xff2d55);
    setTimeout(() => material.color.setHex(0x00f0ff), 350);
  };

  function animate() {
    requestAnimationFrame(animate);
    points.rotation.y += 0.0006;
    points.rotation.x += 0.0002;
    camera.position.x += (mouseX * 6 - camera.position.x) * 0.02;
    camera.position.y += (-mouseY * 6 - camera.position.y) * 0.02;
    camera.lookAt(scene.position);
    renderer.render(scene, camera);
  }
  animate();
})();
