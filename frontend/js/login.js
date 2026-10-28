"use strict";

(() => {
  const form = document.querySelector("#login-form");
  const button = document.querySelector("#login-button");
  const feedback = document.querySelector("#login-feedback");

  if (!form || !button || !feedback) return;

  async function checkSession() {
    try {
      const response = await fetch("/api/auth/me", {
        credentials: "same-origin",
        cache: "no-store"
      });

      if (response.ok) {
        location.replace("/");
      }
    } catch (error) {
      console.error("Session check unavailable", error);
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();

    button.disabled = true;
    feedback.textContent = "Authenticating...";

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username: form.username.value,
          password: form.password.value
        })
      });

      if (!response.ok) {
        throw new Error("Invalid username or password");
      }

      const verify = await fetch("/api/auth/me", {
        credentials: "same-origin",
        cache: "no-store"
      });

      if (!verify.ok) {
        throw new Error(
          "Session unavailable. Use HTTPS for secure login."
        );
      }

      const user = await verify.json();

      if (!Number.isSafeInteger(user.business_id) ||
          user.business_id < 1) {
        throw new Error("Workspace unavailable");
      }

      const url = new URL("/", location.origin);
      url.searchParams.set(
        "business",
        String(user.business_id)
      );

      location.replace(url.toString());
    } catch (error) {
      feedback.textContent = error.message;
      button.disabled = false;
    }
  });

  checkSession();
})();
