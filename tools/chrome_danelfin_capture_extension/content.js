(() => {
  function excerptAround(text, needle, radius = 150) {
    const source = String(text || "");
    const query = String(needle || "");
    if (!source || !query) {
      return "";
    }
    const idx = source.toLowerCase().indexOf(query.toLowerCase());
    if (idx < 0) {
      return "";
    }
    const start = Math.max(0, idx - radius);
    const end = Math.min(source.length, idx + query.length + radius);
    return source.slice(start, end).replace(/\s+/g, " ").trim();
  }

  function containsLiteral(text, needle) {
    return String(text || "").toLowerCase().includes(String(needle || "").toLowerCase());
  }

  function buildDiagnostics() {
    const rawText = String(document.body?.innerText || "");
    const compactText = rawText.replace(/\s+/g, " ").trim();
    const ariaLabels = Array.from(document.querySelectorAll("[aria-label]"))
      .map((el) => String(el.getAttribute("aria-label") || "").trim())
      .filter(Boolean);
    const ariaOutOf10 = ariaLabels.filter((label) => /\b(10|[1-9])\s*out\s+of\s+10\b/i.test(label));
    return {
      requested_url: String(location.href),
      final_url: String(location.href),
      document_title: String(document.title || ""),
      document_ready_state: String(document.readyState || ""),
      body_text_length: rawText.length,
      literals: {
        MU: containsLiteral(rawText, "MU"),
        VRT: containsLiteral(rawText, "VRT"),
        Micron: containsLiteral(rawText, "Micron"),
        Vertiv: containsLiteral(rawText, "Vertiv"),
        "AI Score": containsLiteral(rawText, "AI Score"),
        "out of 10": containsLiteral(rawText, "out of 10"),
        "Last update": containsLiteral(rawText, "Last update"),
        Updated: containsLiteral(rawText, "Updated"),
        Cloudflare: containsLiteral(rawText, "Cloudflare"),
        "Just a moment": containsLiteral(rawText, "Just a moment"),
      },
      excerpts: {
        ai_score: excerptAround(compactText, "AI Score"),
        mu_or_micron: excerptAround(compactText, "MU") || excerptAround(compactText, "Micron"),
        vrt_or_vertiv: excerptAround(compactText, "VRT") || excerptAround(compactText, "Vertiv"),
        last_update: excerptAround(compactText, "Last update") || excerptAround(compactText, "Updated"),
      },
      out_of_10_count: (rawText.match(/\bout\s+of\s+10\b/gi) || []).length,
      aria_label_count: ariaLabels.length,
      aria_out_of_10_count: ariaOutOf10.length,
      aria_out_of_10_samples: ariaOutOf10.slice(0, 8),
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.type === "DIAG_DANELFIN_PAGE") {
      try {
        sendResponse({ ok: true, diagnostics: buildDiagnostics() });
      } catch (err) {
        sendResponse({ ok: false, error: String(err && err.message ? err.message : err) });
      }
      return false;
    }

    if (!message || message.type !== "CAPTURE_DANELFIN") {
      return false;
    }

    try {
      const bodyText = String(document.body?.innerText || "");
      const ariaLabelText = Array.from(document.querySelectorAll("[aria-label]"))
        .map((el) => String(el.getAttribute("aria-label") || "").trim())
        .filter(Boolean)
        .join("\n");
      // Include semantic aria labels because some comparison pages hide numeric score text from innerText.
      const text = [bodyText, ariaLabelText].filter(Boolean).join("\n");
      const capture = self.DanelfinDomParser.parseDanelfinCapture({
        url: String(location.href),
        text,
        expectedSymbols: Array.isArray(message.expectedSymbols) ? message.expectedSymbols : []
      });
      sendResponse({ ok: true, capture });
    } catch (err) {
      sendResponse({ ok: false, error: String(err && err.message ? err.message : err) });
    }
    return false;
  });
})();
