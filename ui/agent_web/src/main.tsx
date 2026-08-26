import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// QtWebEngine versions shipped with some desktop environments expose Web Crypto
// but omit randomUUID. Request IDs are transport correlation IDs, so a local
// fallback keeps the UI functional without weakening command validation.
const cryptoApi = globalThis.crypto as Crypto & { randomUUID?: () => string };
if (cryptoApi && typeof cryptoApi.randomUUID !== "function") {
  Object.defineProperty(cryptoApi, "randomUUID", {
    configurable: true,
    value: () => {
      const part = () => Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, "0");
      return `${part()}-${part().slice(0, 4)}-4${part().slice(0, 3)}-${part().slice(0, 4)}-${part()}${part().slice(0, 4)}`;
    },
  });
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
