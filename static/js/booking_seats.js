// Sync passenger selection to all hidden passenger_id fields
(function () {
  const sel = document.getElementById("passengerSelect");
  if (!sel) return;

  function syncPassenger() {
    const v = sel.value;
    document.querySelectorAll(".passenger-id").forEach((x) => (x.value = v));
  }

  sel.addEventListener("change", syncPassenger);
  syncPassenger();
})();
