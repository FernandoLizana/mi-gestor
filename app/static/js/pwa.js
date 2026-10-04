(function () {
  if (!("serviceWorker" in navigator)) return;

  const base = window.CRM_BASE || "";
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(base + "/sw.js", { scope: base + "/" }).catch(() => {});
  });

  let deferredPrompt = null;
  const installBtn = document.getElementById("pwaInstallBtn");

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) installBtn.hidden = false;
  });

  if (installBtn) {
    installBtn.addEventListener("click", async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      installBtn.hidden = true;
    });
  }
})();
