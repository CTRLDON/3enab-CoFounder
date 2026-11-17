import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";
import { setToken } from "./session";

afterEach(() => { vi.restoreAllMocks(); setToken(null); });

describe("api client", () => {
  it("sends the founder token and parses JSON", async () => {
    setToken("secret");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { headers: { "Content-Type": "application/json" } }));
    await api.venture("v1");
    const headers = fetchMock.mock.calls[0][1]!.headers as Headers;
    expect(headers.get("X-Founder-Token")).toBe("secret");
  });

  it("turns error bodies into ApiError with the backend code", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "approval_required", message: "Approve first." }), { status: 403 }));
    await expect(api.mockPurchase("v1")).rejects.toMatchObject({ status: 403, code: "approval_required", message: "Approve first." });
  });

  it("reports network failures clearly", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.status()).rejects.toBeInstanceOf(ApiError);
  });
});
