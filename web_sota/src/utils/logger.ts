export enum LogLevel {
  INFO = "INFO",
  WARN = "WARN",
  ERROR = "ERROR",
  DEBUG = "DEBUG",
}

export interface LogEntry {
  timestamp: number;
  level: LogLevel;
  message: string;
  context?: unknown;
}

type LogListener = (entry: LogEntry) => void;

class Logger {
  private logs: LogEntry[] = [];
  private maxLogs = 1000;
  private listeners: LogListener[] = [];

  private addLog(level: LogLevel, message: string, context?: unknown) {
    const entry: LogEntry = {
      timestamp: Date.now(),
      level,
      message,
      context,
    };

    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Notify listeners
    for (const listener of this.listeners) {
      listener(entry);
    }

    this.emitConsole(level, message, context);
  }

  private emitConsole(level: LogLevel, message: string, context?: unknown) {
    const style = this.getConsoleStyle(level);
    const ctx = context !== undefined ? context : "";
    switch (level) {
      case LogLevel.ERROR:
        // biome-ignore lint/suspicious/noConsole: <explanation>
        console.error(`%c[MetaMCP] ${message}`, style, ctx);
        break;
      case LogLevel.WARN:
        // biome-ignore lint/suspicious/noConsole: <explanation>
        console.warn(`%c[MetaMCP] ${message}`, style, ctx);
        break;
      case LogLevel.DEBUG:
        // biome-ignore lint/suspicious/noConsole: <explanation>
        console.debug(`%c[MetaMCP] ${message}`, style, ctx);
        break;
      default:
        // biome-ignore lint/suspicious/noConsole: <explanation>
        console.log(`%c[MetaMCP] ${message}`, style, ctx);
    }
  }

  info(message: string, context?: unknown) {
    this.addLog(LogLevel.INFO, message, context);
  }

  warn(message: string, context?: unknown) {
    this.addLog(LogLevel.WARN, message, context);
  }

  error(message: string, context?: unknown) {
    this.addLog(LogLevel.ERROR, message, context);
  }

  debug(message: string, context?: unknown) {
    this.addLog(LogLevel.DEBUG, message, context);
  }

  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  clear() {
    this.logs = [];
    // We could emit a clear event here if needed, but for now we just clear internal state
  }

  on(event: "log", listener: LogListener) {
    if (event === "log") {
      this.listeners.push(listener);
    }
  }

  off(event: "log", listener: LogListener) {
    if (event === "log") {
      this.listeners = this.listeners.filter((l) => l !== listener);
    }
  }

  private getConsoleStyle(level: LogLevel): string {
    switch (level) {
      case LogLevel.INFO:
        return "color: #3b82f6; font-weight: bold";
      case LogLevel.WARN:
        return "color: #eab308; font-weight: bold";
      case LogLevel.ERROR:
        return "color: #ef4444; font-weight: bold";
      case LogLevel.DEBUG:
        return "color: #a855f7; font-weight: bold";
      default:
        return "color: #94a3b8";
    }
  }
}

export const logger = new Logger();
