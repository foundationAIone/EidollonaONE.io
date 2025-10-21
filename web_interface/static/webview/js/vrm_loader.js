import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.159/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.159/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "https://cdn.jsdelivr.net/npm/three@0.159/examples/jsm/loaders/GLTFLoader.js";
import { KTX2Loader } from "https://cdn.jsdelivr.net/npm/three@0.159/examples/jsm/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "https://cdn.jsdelivr.net/npm/three@0.159/examples/jsm/libs/meshopt_decoder.module.js";
import { VRMLoaderPlugin, VRMUtils } from "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@2.0.6/lib/three-vrm.module.js";

const params = new URLSearchParams(window.location.search);
const shouldEnableVrm = params.get("vrm") && params.get("vrm") !== "0" && params.get("vrm") !== "false";

const HUDVRM = {
  enabled: shouldEnableVrm,
  scene: null,
  camera: null,
  renderer: null,
  controls: null,
  clock: null,
  currentVRM: null,
  error: null,
};

function logError(message) {
  HUDVRM.error = message;
  const banner = document.getElementById("avatar-status");
  if (banner) {
    banner.textContent = message;
  }
  console.warn("VRM loader:", message);
}

function initScene(canvas) {
  const scene = new THREE.Scene();
  scene.background = null;

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 1000);
  camera.position.set(0, 1.4, 3.2);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
  });
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.35, 0);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 1.2;
  controls.maxDistance = 4.5;
  controls.maxPolarAngle = Math.PI * 0.48;

  const ambient = new THREE.AmbientLight(0xccccff, 0.75);
  scene.add(ambient);

  const directional = new THREE.DirectionalLight(0xffffff, 1.4);
  directional.position.set(1.5, 2.5, 2.5);
  scene.add(directional);

  const rim = new THREE.DirectionalLight(0x88b9ff, 0.8);
  rim.position.set(-1.4, 2.0, -2.4);
  scene.add(rim);

  HUDVRM.scene = scene;
  HUDVRM.camera = camera;
  HUDVRM.renderer = renderer;
  HUDVRM.controls = controls;
  HUDVRM.clock = new THREE.Clock();

  window.addEventListener("resize", () => resizeRenderer(canvas), { passive: true });
  resizeRenderer(canvas);
}

function resizeRenderer(canvas) {
  if (!HUDVRM.renderer || !HUDVRM.camera) {
    return;
  }
  const card = document.getElementById("avatar-card");
  if (!card) {
    return;
  }
  const width = card.clientWidth || 640;
  const height = width * 0.75;
  HUDVRM.renderer.setSize(width, height, false);
  HUDVRM.camera.aspect = width / height;
  HUDVRM.camera.updateProjectionMatrix();
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
}

function buildLoader(renderer) {
  const loader = new GLTFLoader();
  const ktx2 = new KTX2Loader()
    .setTranscoderPath("https://cdn.jsdelivr.net/npm/three@0.159/examples/jsm/libs/basis/")
    .detectSupport(renderer);
  loader.setKTX2Loader(ktx2);
  loader.setMeshoptDecoder(MeshoptDecoder);
  loader.register((parser) => new VRMLoaderPlugin(parser));
  return loader;
}

function loadVRMAvatar(url) {
  if (!url) {
    logError("No VRM URL supplied. Add ?vrmUrl=/path/to/avatar.vrm");
    return;
  }
  const loader = buildLoader(HUDVRM.renderer);

  loader.load(
    url,
    (gltf) => {
      if (HUDVRM.currentVRM) {
        HUDVRM.scene.remove(HUDVRM.currentVRM.scene);
        HUDVRM.currentVRM = null;
      }
      const vrm = gltf.userData.vrm;
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.removeUnnecessaryJoints(gltf.scene);
      VRMUtils.cleanupVRM(vrm);

      vrm.scene.traverse((obj) => {
        if (obj.isMesh) {
          obj.frustumCulled = false;
          obj.castShadow = true;
        }
      });

      vrm.scene.rotation.y = Math.PI;
      vrm.scene.position.set(0, 0, 0);
      HUDVRM.scene.add(vrm.scene);
      HUDVRM.currentVRM = vrm;
      const banner = document.getElementById("avatar-status");
      if (banner) {
        banner.textContent = "VRM avatar loaded";
      }
      window.dispatchEvent(
        new CustomEvent("hud:vrm-ready", {
          detail: {
            url,
            vrm,
          },
        })
      );
    },
    undefined,
    (err) => {
      logError(`VRM load failed: ${err?.message || err}`);
      window.dispatchEvent(
        new CustomEvent("hud:vrm-error", {
          detail: {
            url,
            message: err?.message || String(err),
          },
        })
      );
    }
  );
}

function animate() {
  requestAnimationFrame(animate);
  if (!HUDVRM.renderer || !HUDVRM.scene || !HUDVRM.camera) {
    return;
  }
  const delta = HUDVRM.clock ? HUDVRM.clock.getDelta() : 0.016;
  if (HUDVRM.currentVRM) {
    HUDVRM.currentVRM.update(delta);
  }
  if (HUDVRM.controls) {
    HUDVRM.controls.update();
  }
  HUDVRM.renderer.render(HUDVRM.scene, HUDVRM.camera);
}

function bootstrap() {
  const card = document.getElementById("avatar-card");
  if (!card) {
    return;
  }
  const canvas = document.getElementById("avatar-canvas");
  if (!canvas) {
    logError("Missing avatar canvas element");
    return;
  }

  const banner = document.getElementById("avatar-status");
  if (banner) {
    banner.textContent = "Initializing VRM pipeline…";
  }

  const supportsWebGL = (() => {
    try {
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      return !!gl;
    } catch (err) {
      return false;
    }
  })();

  if (!supportsWebGL) {
    logError("WebGL not available in this browser. Cannot render VRM avatar.");
    return;
  }

  card.removeAttribute("hidden");
  initScene(canvas);
  animate();

  const defaultUrl = card.dataset.defaultVrm || "";
  const url = params.get("vrmUrl") || defaultUrl;
  if (!url) {
    logError("Set ?vrmUrl=/static/webview/assets/avatars/<file>.vrm to load an avatar.");
    return;
  }
  loadVRMAvatar(url);
}

if (shouldEnableVrm) {
  window.addEventListener("DOMContentLoaded", bootstrap, { once: true });
} else {
  const card = document.getElementById("avatar-card");
  if (card) {
    card.setAttribute("hidden", "hidden");
  }
}

window.HUDVRM = HUDVRM;
