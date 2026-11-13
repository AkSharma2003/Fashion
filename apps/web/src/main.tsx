
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./app/App";
import "./index.css";

// A page restored from the browser's back/forward cache could still show the previous user's details
// (after a logout or a new login). Reload it so it is built again for whoever is signed in now.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) window.location.reload();
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
// Offline app shell for the POS (SRS 5.2). Only in production builds; dev uses Vite's server.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
