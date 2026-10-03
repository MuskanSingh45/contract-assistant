import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { SourceProvider } from "@/components/SourceDrawer";
import { ToastProvider } from "@/components/ui/Toast";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <SourceProvider>
          <App />
        </SourceProvider>
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
