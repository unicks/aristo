import { createRoot } from "react-dom/client";
import { App } from "./App";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./HomePage";
import CreateAssignmentPage from "./CreateAssignmentPage";

// biome-ignore lint/style/noNonNullAssertion: Root element must be there
const container = document.getElementById("root")!;
const root = createRoot(container);
root.render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/check" element={<App />} />
      <Route path="/create" element={<CreateAssignmentPage />} />
    </Routes>
  </BrowserRouter>
);
