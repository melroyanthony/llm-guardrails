(function () {
  var scheme = new URLSearchParams(window.location.search).get("scheme");
  if (scheme === "slate" || scheme === "default") {
    document.body.setAttribute("data-md-color-scheme", scheme);
  }
  var button = document.getElementById("fg-copy");
  var command = document.getElementById("fg-install-cmd");
  if (!button || !command) {
    return;
  }
  button.addEventListener("click", function () {
    var text = command.textContent || "";
    var done = function () {
      button.textContent = "Copied";
      window.setTimeout(function () {
        button.textContent = "Copy";
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, done);
      return;
    }
    done();
  });
})();
