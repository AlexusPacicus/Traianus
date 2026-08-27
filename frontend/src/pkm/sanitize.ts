/**
 * PKM clinical/somatic sanitization rule — single source for the .purgativa
 * stream and /ingesta pre-filtering. NotebookLM origin, NOT a substrate rule.
 */
export const CLINICAL_REGEX = new RegExp(
  String.raw`\b(tdah|adhd|ansiedad|depresi[óo]n|depresivo|bipolar|trastorno|d[eé]ficit\s+de\s+atenci[óo]n|paciente|cl[íi]nico|diagn[óo]stico|patolog[íi]a|s[íi]ntoma|tratamiento|borderline)\b`,
  "gi"
);

export function sanitizeSomaticFlow(text: string): { sanitized: string; flagged: boolean } {
  const flagged = CLINICAL_REGEX.test(text);
  CLINICAL_REGEX.lastIndex = 0;
  if (!flagged) return { sanitized: text, flagged: false };
  const sanitized = text.replace(CLINICAL_REGEX, "[Estímulo Somático Desplazado]");
  CLINICAL_REGEX.lastIndex = 0;
  return { sanitized, flagged: true };
}
