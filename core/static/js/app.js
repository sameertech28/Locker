// General interactivity shared across app pages.
document.addEventListener("DOMContentLoaded", () => {

  // --- Drag & drop upload zone --------------------------------------------
  document.querySelectorAll(".dropzone").forEach((zone) => {
    const input = zone.querySelector('input[type="file"]');
    if (!input) return;
    const label = zone.querySelector("[data-filename]");

    zone.addEventListener("click", () => input.click());
    ["dragenter", "dragover"].forEach((evt) =>
      zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.add("drag-over"); })
    );
    ["dragleave", "drop"].forEach((evt) =>
      zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.remove("drag-over"); })
    );
    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        if (label) label.textContent = e.dataTransfer.files[0].name;
      }
    });
    input.addEventListener("change", () => {
      if (input.files.length && label) label.textContent = input.files[0].name;
    });
  });

  // --- Favorite star toggle (AJAX) ---------------------------------------
  document.querySelectorAll(".fav-star").forEach((star) => {
    star.addEventListener("click", async (e) => {
      e.preventDefault();
      const url = star.dataset.url;
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      try {
        const res = await fetch(url, { method: "POST", headers: { "X-CSRFToken": csrftoken, "X-Requested-With": "XMLHttpRequest" } });
        const data = await res.json();
        star.classList.toggle("active", data.is_favorite);
      } catch (err) {
        console.error("Favorite toggle failed", err);
      }
    });
  });

  // --- Toast auto-dismiss ---------------------------------------------------
  document.querySelectorAll(".toast").forEach((toast) => {
    setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity .4s"; }, 4000);
    setTimeout(() => toast.remove(), 4500);
  });

  // --- Notification badge polling -------------------------------------------
  const badge = document.getElementById("notif-badge");
  if (badge) {
    setInterval(async () => {
      try {
        const res = await fetch("/notifications/poll/");
        const data = await res.json();
        if (data.unread > 0) {
          badge.textContent = data.unread;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      } catch (err) { /* silent */ }
    }, 20000);
  }
});
