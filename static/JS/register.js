(function () {
  const form = document.getElementById("register-form");
  const pw = document.getElementById("password");
  const meter = document.getElementById("strength");
  const meterLabel = document.getElementById("strength-label");

  function setError(field, msg) {
    document.getElementById("err-" + field).textContent = msg || "";
  }

  // same rules the server enforces
  function passwordOk(p) {
    return p.length >= 8 && /\d/.test(p) && /[A-Z]/.test(p);
  }

  function scorePassword(p) {
    let s = 0;
    if (p.length >= 8) s++;
    if (/\d/.test(p)) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    return s;
  }

  const LABELS = ["-", "Weak", "Fair", "Good", "Strong"];

  pw.addEventListener("input", function () {
    const s = pw.value ? scorePassword(pw.value) : 0;
    meter.className = "strength s" + s;
    meterLabel.textContent = "Strength: " + LABELS[s];
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    ["username", "password", "confirm"].forEach(function (f) { setError(f, ""); });

    const username = document.getElementById("username").value.trim();
    const password = pw.value;
    const confirm = document.getElementById("confirm").value;

    let bad = false;
    if (username.length < 3 || username.length > 40) {
      setError("username", "Username must be 3 to 40 characters"); bad = true;
    }
    if (!passwordOk(password)) {
      setError("password", "Need 8+ chars, a number and an uppercase letter"); bad = true;
    }
    if (password !== confirm) {
      setError("confirm", "Passwords do not match"); bad = true;
    }
    if (bad) return;

    try {
      const res = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          username: username,
          password: password,
          confirm_password: confirm,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.error && data.error.toLowerCase().indexOf("username") !== -1) {
          setError("username", data.error);
        } else {
          setError("password", data.error || "Registration failed");
        }
        return;
      }
      window.location = data.redirect || "/dashboard";
    } catch (err) {
      toast("Could not reach the server", "error");
    }
  });
})();
