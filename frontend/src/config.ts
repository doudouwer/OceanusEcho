/** MC1 `Person.id`, stored as `original_id` in Neo4j — default narrative lead Sailor Shift */
export const DEFAULT_SAILOR_PERSON_ID =
  (import.meta.env.VITE_DEFAULT_PERSON_ID as string | undefined)?.trim() || "17255";

export const DEFAULT_SAILOR_NAME = "Sailor Shift";

/** Ivy Echoes members (same data-source ids) for one-click compare */
export const IVY_ECHOES_BANDMATES: { id: string; name: string }[] = [
  { id: "17256", name: "Maya Jensen" },
  { id: "17257", name: "Lila \"Lilly\" Hartman" },
  { id: "17258", name: "Jade Thompson" },
  { id: "17259", name: "Sophie Ramirez" },
];
