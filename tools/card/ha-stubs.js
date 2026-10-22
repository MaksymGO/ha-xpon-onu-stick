// Stand-ins for the Home Assistant frontend elements the card uses, so it can
// run outside Home Assistant. They copy the default look, not the behavior.
(() => {
  const MDI = {
    "mdi:access-point-network":
      "M4.93,3.93C3.12,5.74 2,8.24 2,11C2,13.76 3.12,16.26 4.93,18.07L6.34,16.66C4.89,15.22 4,13.22 4,11C4,8.79 4.89,6.78 6.34,5.34L4.93,3.93M19.07,3.93L17.66,5.34C19.11,6.78 20,8.79 20,11C20,13.22 19.11,15.22 17.66,16.66L19.07,18.07C20.88,16.26 22,13.76 22,11C22,8.24 20.88,5.74 19.07,3.93M7.76,6.76C6.67,7.85 6,9.35 6,11C6,12.65 6.67,14.15 7.76,15.24L9.17,13.83C8.45,13.11 8,12.11 8,11C8,9.89 8.45,8.89 9.17,8.17L7.76,6.76M16.24,6.76L14.83,8.17C15.55,8.89 16,9.89 16,11C16,12.11 15.55,13.11 14.83,13.83L16.24,15.24C17.33,14.15 18,12.65 18,11C18,9.35 17.33,7.85 16.24,6.76M12,9A2,2 0 0,0 10,11A2,2 0 0,0 12,13A2,2 0 0,0 14,11A2,2 0 0,0 12,9M11,15V19H10A1,1 0 0,0 9,20H2V22H9A1,1 0 0,0 10,23H14A1,1 0 0,0 15,22H22V20H15A1,1 0 0,0 14,19H13V15H11Z",
  };

  customElements.define(
    "ha-card",
    class extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: "open" }).innerHTML = `<style>
          :host {
            display: block;
            background: var(--ha-card-background, var(--card-background-color, #fff));
            border: 1px solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
            border-radius: var(--ha-card-border-radius, 12px);
            color: var(--primary-text-color);
          }
        </style><slot></slot>`;
      }
    },
  );

  customElements.define(
    "ha-icon",
    class extends HTMLElement {
      static get observedAttributes() {
        return ["icon"];
      }

      connectedCallback() {
        this._render();
      }

      attributeChangedCallback() {
        this._render();
      }

      _render() {
        if (!this.shadowRoot) this.attachShadow({ mode: "open" });
        this.shadowRoot.innerHTML = `<style>
          :host { display: inline-flex; }
          svg { width: var(--mdc-icon-size, 24px); height: var(--mdc-icon-size, 24px); }
        </style><svg viewBox="0 0 24 24"><path fill="currentColor" d="${MDI[this.getAttribute("icon")] || ""}"></path></svg>`;
      }
    },
  );

  // Renders the card editor's schema as plain inputs and reports changes the
  // way ha-form does, with a value-changed event carrying the whole form data.
  customElements.define(
    "ha-form",
    class extends HTMLElement {
      set hass(hass) {
        this._hass = hass;
        this._render();
      }

      set schema(schema) {
        this._schema = schema;
        this._render();
      }

      set data(data) {
        this._data = data;
        this._render();
      }

      get data() {
        return this._data;
      }

      _render() {
        if (!this._hass || !this._schema || !this._data) return;
        const fields = this._schema.flatMap((item) => item.schema || [item]);
        this.replaceChildren(...fields.map((field) => this._field(field)));
      }

      _field(field) {
        const label = document.createElement("label");
        const value = this._data[field.name];
        let input;
        if (field.selector?.boolean) {
          input = document.createElement("input");
          input.type = "checkbox";
          input.checked = Boolean(value);
        } else if (field.selector?.device) {
          input = document.createElement("select");
          const devices = Object.values(this._hass.devices || {});
          for (const device of [{ id: "", name: "Automatic" }, ...devices]) {
            input.add(new Option(device.name, device.id, false, device.id === (value || "")));
          }
        } else {
          input = document.createElement("input");
          input.type = "text";
          input.value = value ?? "";
        }
        input.name = field.name;
        input.addEventListener("change", () => {
          const next = input.type === "checkbox" ? input.checked : input.value;
          this.dispatchEvent(
            new CustomEvent("value-changed", { detail: { value: { ...this._data, [field.name]: next } } }),
          );
        });
        const text = this.computeLabel ? this.computeLabel(field) : field.name;
        label.append(input, document.createTextNode(` ${text}`));
        return label;
      }
    },
  );
})();
