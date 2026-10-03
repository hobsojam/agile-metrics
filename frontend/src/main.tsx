import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Could not find #root element to mount the app into");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
