import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// 部分 QtWebEngine 缺少 randomUUID，使用本地请求标识作为兼容方案。
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
