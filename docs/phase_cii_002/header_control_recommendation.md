# Header Control Recommendation — Phase CII-002

## Implemented: Option D — "About CII" Pill

### CSS
```css
.cii-about-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 9px 2px 7px;
  border-radius: 12px;
  background: var(--accent); color: #fff;
  font-size: 0.70rem; font-weight: 700; letter-spacing: 0.03em;
  border: none; cursor: pointer;
  vertical-align: middle; margin-left: 6px;
  transition: opacity 0.15s;
}
.cii-about-btn:hover { opacity: 0.85; }
```

### HTML
```html
<button class="cii-about-btn" onclick="_openCIIModal()"
        title="About Consensus Intelligence Investing"
        aria-label="About Consensus Intelligence Investing">
  ⓘ About CII
</button>
```

### Accessibility
- Keyboard focusable (`<button>` element)
- `title` attribute for tooltip
- `aria-label` for screen readers
- Color contrast: white (#fff) on teal (#0d5c63) — contrast ratio ~7.5:1 (exceeds WCAG AA and AAA)

### Visual Result
The button renders as a small teal pill with white text immediately after the tagline, clearly inviting the operator to learn more about the methodology. It is the only colored element in the subtitle row, making it the natural focus point for a new user.
