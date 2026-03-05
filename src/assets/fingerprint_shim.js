(() => {
  // --- helpers ---
  const defineGetter = (obj, prop, value) => {
    try {
      Object.defineProperty(obj, prop, { get: () => value, configurable: true });
    } catch {}
  };

  // --- Navigator: language(s), platform, webdriver, concurrency ---
  defineGetter(Navigator.prototype, "hardwareConcurrency", 8);
  defineGetter(Navigator.prototype, "language", "en-GB");
  defineGetter(Navigator.prototype, "languages", ["en-GB", "en"]);
  defineGetter(Navigator.prototype, "platform", "MacIntel");
  defineGetter(Navigator.prototype, "webdriver", undefined);

  // --- Permissions: avoid Illegal return + keep shape predictable ---
  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (parameters) => {
      try {
        if (parameters && parameters.name === "notifications") {
          // PermissionStatus-like object
          return Promise.resolve({
            state: Notification.permission,
            onchange: null,
          });
        }
      } catch {}
      return originalQuery(parameters);
    };
  }

  // --- Canvas: deterministic, lightweight perturbation ---
  // NOTE: This is for reproducible testing. It intentionally avoids heavy per-pixel loops.
  const seed = 1337; // make this configurable per test run if you want
  let s = seed >>> 0;
  const rand = () => (s = (s * 1664525 + 1013904223) >>> 0) / 2**32;

  const patchCanvasExport = (name) => {
    const orig = HTMLCanvasElement.prototype[name];
    if (!orig) return;

    Object.defineProperty(HTMLCanvasElement.prototype, name, {
      value: function(...args) {
        try {
          const ctx = this.getContext("2d");
          if (ctx) {
            // tiny, deterministic 1px shift in a corner (minimal impact, low cost)
            const w = this.width | 0, h = this.height | 0;
            if (w > 0 && h > 0) {
              const x = (rand() * Math.min(8, w)) | 0;
              const y = (rand() * Math.min(8, h)) | 0;
              const img = ctx.getImageData(x, y, 1, 1);
              // slight clamped change
              img.data[0] = (img.data[0] + 1) & 255;
              ctx.putImageData(img, x, y);
            }
          }
        } catch {
          // ignore tainted canvas / security errors
        }
        return orig.apply(this, args);
      },
      configurable: true
    });
  };

  patchCanvasExport("toDataURL");
  patchCanvasExport("toBlob");

  // --- WebGL: patch safely (WebGL1 + WebGL2) ---
  const patchWebGL = (proto) => {
    if (!proto || !proto.getParameter) return;
    const origGetParameter = proto.getParameter;

    Object.defineProperty(proto, "getParameter", {
      value: function(parameter) {
        // 37445/37446 are often used, but many scripts use WEBGL_debug_renderer_info constants.
        // We only override known IDs and otherwise call through.
        if (parameter === 37445) return "ANGLE (Intel, Intel(R) Iris(TM) Graphics, OpenGL 4.1)";
        if (parameter === 37446) return "Google Inc.";
        return origGetParameter.call(this, parameter);
      },
      configurable: true
    });

    const origGetExtension = proto.getExtension;
    if (origGetExtension) {
      Object.defineProperty(proto, "getExtension", {
        value: function(name) {
          const ext = origGetExtension.call(this, name);
          if (name === "WEBGL_debug_renderer_info" && ext) {
            // keep ext but ensure constants exist
            return ext;
          }
          return ext;
        },
        configurable: true
      });
    }
  };

  patchWebGL(WebGLRenderingContext && WebGLRenderingContext.prototype);
  patchWebGL(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
})();
