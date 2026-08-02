import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BuildersPage } from "./Builders";

const mockCreateProject = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    createProject: (...args: unknown[]) => mockCreateProject(...args),
  },
  getErrorMessage: (r: unknown) => (r as { message?: string })?.message ?? "Error",
  isSuccessResponse: (r: unknown) => !!(r as { success?: boolean })?.success,
}));

describe("BuildersPage", () => {
  it("renders Spec Kit (SDD) card", () => {
    render(<BuildersPage />);
    expect(screen.getByText("Spec Kit (SDD)")).toBeInTheDocument();
    expect(screen.getByText(/GitHub Spec-Driven Development/)).toBeInTheDocument();
  });

  it("opens SpecKitModal on card click", async () => {
    render(<BuildersPage />);
    const card = screen.getByText("Spec Kit (SDD)");
    await userEvent.click(card);

    expect(screen.getByText("Spec Kit Scaffold")).toBeInTheDocument();
    expect(screen.getByLabelText(/Project Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Output Path/)).toBeInTheDocument();
    expect(screen.getByLabelText(/AI Coding Agent/)).toBeInTheDocument();
    expect(screen.getByText("Run specify init")).toBeInTheDocument();
  });

  it("submits spec-kit scaffold with opencode default", async () => {
    mockCreateProject.mockResolvedValueOnce({
      success: true,
      message: "Spec Kit project 'my-server' scaffolded!",
    });

    render(<BuildersPage />);
    const card = screen.getByText("Spec Kit (SDD)");
    await userEvent.click(card);

    await userEvent.type(screen.getByLabelText(/Project Name/), "my-server");
    await userEvent.type(screen.getByLabelText(/Output Path/), "D:\\Dev\\repos");

    await userEvent.click(screen.getByText("Run specify init"));

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith({
        template_type: "spec_kit",
        project_name: "my-server",
        output_path: "D:\\Dev\\repos",
        features: { ai_integration: "opencode" },
      });
    });
  });

  it("submits with different AI integration", async () => {
    mockCreateProject.mockResolvedValueOnce({
      success: true,
      message: "Spec Kit project 'test' scaffolded!",
    });

    render(<BuildersPage />);
    const card = screen.getByText("Spec Kit (SDD)");
    await userEvent.click(card);

    await userEvent.type(screen.getByLabelText(/Project Name/), "test");
    await userEvent.type(screen.getByLabelText(/Output Path/), "/tmp");

    const select = screen.getByLabelText(/AI Coding Agent/);
    await userEvent.selectOptions(select, "claude");

    await userEvent.click(screen.getByText("Run specify init"));

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith(
        expect.objectContaining({
          template_type: "spec_kit",
          features: { ai_integration: "claude" },
        }),
      );
    });
  });

  it("shows error state on API failure", async () => {
    mockCreateProject.mockResolvedValueOnce({
      success: false,
      message: "specify CLI not found",
    });

    render(<BuildersPage />);
    const card = screen.getByText("Spec Kit (SDD)");
    await userEvent.click(card);

    await userEvent.type(screen.getByLabelText(/Project Name/), "fail");
    await userEvent.type(screen.getByLabelText(/Output Path/), "/tmp");
    await userEvent.click(screen.getByText("Run specify init"));

    await waitFor(() => {
      expect(screen.getByText(/specify CLI not found/)).toBeInTheDocument();
    });
  });
});
