import { describe, expect, it } from "vitest";
import { formatBytes } from "./format";

describe("formatBytes", () => {
  it("formats kilobytes and megabytes", () => {
    expect(formatBytes(1_024)).toBe("1 KB");
    expect(formatBytes(1_572_864)).toBe("1.5 MB");
  });
});
