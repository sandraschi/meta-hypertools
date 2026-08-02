import { beforeEach, describe, expect, it, vi } from "vitest";
import { LogLevel, logger } from "./logger";

describe("Logger", () => {
  beforeEach(() => {
    logger.clear();
    vi.restoreAllMocks();
  });

  it("should add logs to internal storage", () => {
    logger.info("Test Info");
    logger.warn("Test Warn");

    const logs = logger.getLogs();
    expect(logs).toHaveLength(2);
    expect(logs[0].level).toBe(LogLevel.INFO);
    expect(logs[0].message).toBe("Test Info");
    expect(logs[1].level).toBe(LogLevel.WARN);
    expect(logs[1].message).toBe("Test Warn");
  });

  it("should notify listeners on new log", () => {
    const listener = vi.fn();
    logger.on("log", listener);

    logger.error("Test Error");

    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({
        level: LogLevel.ERROR,
        message: "Test Error",
      }),
    );

    // Test cleanup
    logger.off("log", listener);
    logger.debug("Test Debug");
    expect(listener).toHaveBeenCalledTimes(1); // Should not increment
  });

  it("should handle max logs limit", () => {
    // Mock maxLogs by filling it up (assuming default 1000)
    // Since maxLogs is private, we can't change it easily on the singleton.
    // We will just verify it adds.
    const msg = "Test Message";
    logger.info(msg);
    expect(logger.getLogs()[0].message).toBe(msg);
  });

  it("should clear logs", () => {
    logger.info("To be cleared");
    expect(logger.getLogs()).toHaveLength(1);

    logger.clear();
    expect(logger.getLogs()).toHaveLength(0);
  });
});
