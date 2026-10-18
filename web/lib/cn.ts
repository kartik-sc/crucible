/** Join class names, dropping falsy entries — a dependency-free stand-in for clsx. */
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
