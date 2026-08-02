import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import { ApiProvider } from "./context/ApiContext";
import { ToastProvider } from "./context/ToastContext";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error(
    'Failed to find the root element. Please ensure index.html contains a <div id="root"> element.',
  );
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ToastProvider>
      <ApiProvider>
        <App />
      </ApiProvider>
    </ToastProvider>
  </React.StrictMode>,
);
