/** MC1 `Person.id`，导入 Neo4j 后为 `original_id` — 默认叙事主角 Sailor Shift */
export const DEFAULT_SAILOR_PERSON_ID =
  (import.meta.env.VITE_DEFAULT_PERSON_ID as string | undefined)?.trim() || "17255";

export const DEFAULT_SAILOR_NAME = "Sailor Shift";

/** Ivy Echoes 成员（同一数据源 id），用于一键加入对比 */
export const IVY_ECHOES_BANDMATES: { id: string; name: string }[] = [
  { id: "17256", name: "Maya Jensen" },
  { id: "17257", name: "Lila \"Lilly\" Hartman" },
  { id: "17258", name: "Jade Thompson" },
  { id: "17259", name: "Sophie Ramirez" },
];
