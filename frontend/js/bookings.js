"use strict";

(() => {
  const panel = document.querySelector("#appointments");
  if (!panel) return;

  const businessId = Number(
    new URLSearchParams(location.search).get("business")
  );

  const section = document.createElement("section");
  section.className = "booking-section";

  section.innerHTML = `
    <div class="panel-head">
      <h3>GNOMEbook · Appointments</h3>
      <span class="pill">Live Calendar</span>
    </div>

    <form id="booking-form">
      <label>
        Appointment Title
        <input name="title" required
          maxlength="200"
          placeholder="Client consultation">
      </label>

      <label>
        Date & Time
        <input name="starts_at"
          type="datetime-local" required>
      </label>

      <label>
        Notes
        <textarea name="notes"
          maxlength="5000"
          placeholder="Meeting details"></textarea>
      </label>

      <button type="submit">Book Appointment</button>
      <p id="booking-message" role="status"></p>
    </form>

    <div id="booking-list"></div>
  `;

  panel.append(section);

  const form = section.querySelector("#booking-form");
  const list = section.querySelector("#booking-list");
  const message = section.querySelector("#booking-message");

  async function loadBookings() {
    if (!Number.isSafeInteger(businessId) || businessId < 1) {
      list.textContent = "Select a business first.";
      return;
    }

    try {
      const response = await fetch(
        `/api/businesses/${businessId}/appointments`
      );

      if (!response.ok) throw new Error("Unable to load bookings");

      const data = await response.json();
      list.replaceChildren();

      if (!data.appointments.length) {
        list.textContent = "No appointments scheduled.";
        return;
      }

      for (const booking of data.appointments) {
        const card = document.createElement("article");
        card.className = "booking-card";

        const title = document.createElement("strong");
        title.textContent = booking.title;

        const detail = document.createElement("small");
        detail.textContent =
          `${new Date(booking.starts_at).toLocaleString()} · ${booking.status}`;

        card.append(title, detail);

        if (booking.status === "scheduled") {
          for (const status of ["completed", "cancelled"]) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent =
              status === "completed" ? "Complete" : "Cancel";

            button.addEventListener("click", async () => {
              button.disabled = true;

              try {
                const response = await fetch(
                  `/api/appointments/${booking.id}`,
                  {
                    method: "PATCH",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({status})
                  }
                );

                if (!response.ok) throw new Error("Update failed");
                await loadBookings();
              } catch (error) {
                message.textContent = error.message;
                button.disabled = false;
              }
            });

            card.append(button);
          }
        }

        list.append(card);
      }
    } catch (error) {
      list.textContent = error.message;
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const button = form.querySelector('[type="submit"]');
    const values = new FormData(form);
    const localTime = values.get("starts_at");
    const timestamp = new Date(localTime);

    if (!Number.isSafeInteger(businessId) ||
        businessId < 1 ||
        Number.isNaN(timestamp.getTime())) {
      message.textContent = "Choose a business and valid time.";
      return;
    }

    button.disabled = true;
    message.textContent = "";

    try {
      const response = await fetch("/api/appointments", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          business_id: businessId,
          title: values.get("title"),
          starts_at: timestamp.toISOString(),
          notes: values.get("notes")
        })
      });

      if (!response.ok) throw new Error("Booking failed");

      form.reset();
      message.textContent = "Appointment booked!";
      await loadBookings();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });

  loadBookings();
})();
