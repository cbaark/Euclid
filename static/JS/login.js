// login screen. plain fetch here since /login is csrf exempt and pre-session

(function () {
  const form = document.getElementById("login-form");

  function setError(field, msg) {
    document.getElementById("err-" + field).textContent = msg || "";
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    setError("username", "");
    setError("password", "");

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const remember = document.getElementById("remember").checked;

    let bad = false;
    if (!username) { setError("username", "Username is required"); bad = true; }
    if (!password) { setError("password", "Password is required"); bad = true; }
    if (bad) return;

    try {
      const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ username: username, password: password, remember: remember }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError("password", data.error || "Login failed");
        return;
      }
      window.location = data.redirect || "/dashboard";
    } catch (err) {
      toast("Could not reach the server", "error");
    }
  });
})();
