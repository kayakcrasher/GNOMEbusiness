"use strict";

window.gnomeWorkspace = (async () => {
  const params = new URLSearchParams(location.search);
  const requested = params.get("business");
  const saved = localStorage.getItem("gnome_business_id");
  const id = requested || saved;

  if (id && /^[1-9]\d*$/.test(id)) {
    const response = await fetch(
      `/api/businesses/${id}/dashboard`
    );

    if (response.ok) {
      localStorage.setItem("gnome_business_id", id);
      return Number(id);
    }
  }

  const response = await fetch("/api/businesses", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      name: "GNOME Demo Company"
    })
  });

  if (!response.ok) {
    throw new Error("Workspace creation failed");
  }

  const business = await response.json();

  localStorage.setItem(
    "gnome_business_id",
    String(business.id)
  );

  return business.id;
})();

window.gnomeWorkspace.then(id => {
  const url = new URL(location.href);

  if (url.searchParams.get("business") !== String(id)) {
    url.searchParams.set("business", String(id));
    location.replace(url.toString());
  }
}).catch(console.error);
