(function () {
  const DEFAULT_TARGET_ID = "cap-log";
  const MAX_LINES = 200;

  function appendLine(target, text) {
    if (!target) {
      return;
    }
    const line = document.createElement("div");
    line.textContent = text;
    target.prepend(line);
    while (target.childElementCount > MAX_LINES) {
      target.removeChild(target.lastChild);
    }
  }

  const AuditStream = {
    _source: null,
    _url: "",
    _retryDelay: 2000,
    _maxDelay: 15000,
    _stopped: false,
    _target: null,
    _callback: null,

    start(url, options) {
      if (!url) {
        return;
      }
      const opts = options || {};
      this._url = url;
      this._retryDelay = 2000;
      this._stopped = false;
      this._target = opts.target || (opts.targetId ? document.getElementById(opts.targetId) : document.getElementById(DEFAULT_TARGET_ID));
      this._callback = typeof opts.onData === "function" ? opts.onData : null;
      this._open();
    },

    stop() {
      this._stopped = true;
      if (this._source) {
        try {
          this._source.close();
        } catch (err) {
          console.debug("AuditStream close", err);
        }
        this._source = null;
      }
    },

    _open() {
      if (this._stopped || !this._url) {
        return;
      }
      if (this._source) {
        try {
          this._source.close();
        } catch (err) {
          console.debug("AuditStream reopen", err);
        }
        this._source = null;
      }
      try {
        const source = new EventSource(this._url, { withCredentials: false });
        this._source = source;
        source.onmessage = (event) => {
          this._retryDelay = 2000;
          if (this._stopped) {
            return;
          }
          const text = event.data || "";
          if (this._callback) {
            try {
              this._callback(text);
            } catch (err) {
              console.warn("AuditStream callback error", err);
            }
          } else {
            appendLine(this._target, text);
          }
        };
        source.onerror = () => {
          if (this._stopped) {
            return;
          }
          try {
            source.close();
          } catch (err) {
            console.debug("AuditStream error close", err);
          }
          const delay = this._retryDelay;
          this._retryDelay = Math.min(this._retryDelay * 2, this._maxDelay);
          setTimeout(() => this._open(), delay);
        };
      } catch (err) {
        console.warn("AuditStream open failed", err);
        const delay = this._retryDelay;
        this._retryDelay = Math.min(this._retryDelay * 2, this._maxDelay);
        setTimeout(() => this._open(), delay);
      }
    },
  };

  window.AuditStream = AuditStream;
})();
