import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SystemStatusPage from "../pages/SystemStatusPage";
import * as health from "../api/health";

vi.mock("../api/health");

const renderPage = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SystemStatusPage />
    </QueryClientProvider>,
  );

test("shows API and database as healthy when both endpoints respond", async () => {
  vi.mocked(health.fetchLiveness).mockResolvedValue({ status: "ok" });
  vi.mocked(health.fetchReadiness).mockResolvedValue({ status: "ready", database: "ok" });
  const { container } = renderPage();
  await screen.findByText("API");
  await vi.waitFor(() => expect(container.querySelectorAll(".text-emerald-600")).toHaveLength(2));
});

test("surfaces an error when the API is unreachable", async () => {
  vi.mocked(health.fetchLiveness).mockRejectedValue(new Error("network"));
  vi.mocked(health.fetchReadiness).mockRejectedValue(new Error("network"));
  renderPage();
  expect(await screen.findByText("Cannot reach the API")).toBeInTheDocument();
  expect(await screen.findByText("Not ready")).toBeInTheDocument();
});
