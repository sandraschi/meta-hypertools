/** Split large inspire_repo_* text blobs into navigable chapters. */

export type InspirationChapter = {
  id: string;

  title: string;

  body: string;

  lineCount: number;

  kind?: string;
};

export type ServerInspirationChapter = {
  id: string;

  title: string;

  kind: string;

  body: string;
};

const CHAPTER_LINE = /^(#{1,3}\s|━━━\s|═{3,}|─{10,}\s*$|💡\s|⚠️\s|📦\s|📊\s|📁\s|\*\*Your task)/;

function cleanTitle(line: string): string {
  const t = line

    .replace(/^#+\s*/, "")

    .replace(/^━━━\s*/, "")

    .replace(/^═+\s*/, "")

    .trim();

  return t.length > 100 ? `${t.slice(0, 97)}…` : t || "Section";
}

function toUiChapter(ch: ServerInspirationChapter): InspirationChapter {
  const body = ch.body ?? "";

  return {
    id: ch.id,

    title: ch.title,

    body,

    lineCount: body ? body.split(/\r?\n/).length : 0,

    kind: ch.kind,
  };
}

/** Prefer server-structured chapters when present (Phase A). */

export function resolveInspirationChapters(
  payload: unknown,
  fallbackText: string,
): InspirationChapter[] {
  if (payload && typeof payload === "object") {
    const root = payload as Record<string, unknown>;

    const data = (root.data ?? root.result ?? root) as Record<string, unknown>;

    const inner =
      data.data && typeof data.data === "object" ? (data.data as Record<string, unknown>) : data;

    const chapters = inner.chapters;

    if (Array.isArray(chapters) && chapters.length > 0) {
      return chapters

        .filter((c): c is ServerInspirationChapter => {
          if (!c || typeof c !== "object") return false;

          const row = c as Record<string, unknown>;

          return typeof row.body === "string";
        })

        .map((c) => toUiChapter(c as ServerInspirationChapter));
    }
  }

  return splitInspirationChapters(fallbackText);
}

/** Split on markdown headings, file fences, horizontal rules, and prompt section markers. */

export function splitInspirationChapters(text: string): InspirationChapter[] {
  if (!text.trim()) {
    return [{ id: "ch-0", title: "Empty", body: "", lineCount: 0 }];
  }

  const lines = text.split(/\r?\n/);

  const chapters: InspirationChapter[] = [];

  let title = "Overview";

  let buffer: string[] = [];

  let index = 0;

  const flush = () => {
    const body = buffer.join("\n").trim();

    if (body.length > 0 || chapters.length === 0) {
      chapters.push({
        id: `ch-${index++}`,

        title,

        body,

        lineCount: body ? body.split("\n").length : 0,
      });
    }

    buffer = [];
  };

  for (const line of lines) {
    if (CHAPTER_LINE.test(line)) {
      if (buffer.length > 0) {
        flush();
      }

      title = cleanTitle(line);

      buffer.push(line);
    } else {
      buffer.push(line);
    }
  }

  flush();

  return chapters;
}

export function extractInspirationText(payload: unknown): string {
  if (payload == null) return "";

  if (typeof payload === "string") return payload;

  if (typeof payload === "object") {
    const root = payload as Record<string, unknown>;

    const data = root.data as Record<string, unknown> | undefined;

    if (data && typeof data.text === "string") return data.text;

    if (typeof root.text === "string") return root.text;

    const result = root.result as Record<string, unknown> | undefined;

    if (result?.data && typeof (result.data as Record<string, unknown>).text === "string") {
      return (result.data as Record<string, unknown>).text as string;
    }

    if (result && typeof result.data === "object") {
      const inner = result.data as Record<string, unknown>;

      if (typeof inner.text === "string") return inner.text;
    }

    if (typeof root.message === "string" && root.success === false) return root.message;
  }

  return JSON.stringify(payload, null, 2);
}
