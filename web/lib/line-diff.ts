/**
 * A small LCS line diff for the Builder's patch view (v1 → v2). Builder answers
 * are a few dozen lines at most, so the O(n·m) table is fine.
 */

export type DiffKind = "same" | "added" | "removed";

export interface DiffLine {
  kind: DiffKind;
  text: string;
  /** 1-based line number in the new version (absent for removed lines). */
  lineNo?: number;
}

export function diffLines(prev: string, next: string): DiffLine[] {
  const a = prev.split("\n");
  const b = next.split("\n");
  const w = b.length + 1;
  // lcs[i * w + j] = length of the LCS of a[i..] and b[j..]
  const lcs = new Uint16Array((a.length + 1) * w);
  const at = (i: number, j: number) => lcs[i * w + j] ?? 0;
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i * w + j] = a[i] === b[j] ? at(i + 1, j + 1) + 1 : Math.max(at(i + 1, j), at(i, j + 1));
    }
  }

  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    const left = a[i];
    const right = b[j];
    if (left !== undefined && right !== undefined && left === right) {
      out.push({ kind: "same", text: right, lineNo: j + 1 });
      i++;
      j++;
    } else if (left !== undefined && (right === undefined || at(i + 1, j) >= at(i, j + 1))) {
      out.push({ kind: "removed", text: left });
      i++;
    } else {
      out.push({ kind: "added", text: right ?? "", lineNo: j + 1 });
      j++;
    }
  }
  return out;
}

/** The first version has nothing to compare against: every line is plain. */
export function plainLines(text: string): DiffLine[] {
  return text.split("\n").map((line, i) => ({ kind: "same", text: line, lineNo: i + 1 }));
}
