"""与 MC1_graph.json 导入 Neo4j 后的约定（可在 .env 覆盖）。"""

# JSON 边类型为 PascalCase，例如 PerformerOf、InStyleOf
DEFAULT_REL_TYPES: dict[str, str] = {
    "PERFORMER_OF": "PerformerOf",
    "IN_STYLE_OF": "InStyleOf",
    "INTERPOLATES_FROM": "InterpolatesFrom",
    "COMPOSER_OF": "ComposerOf",
    "LYRICIST_OF": "LyricistOf",
    "RECORDED_BY": "RecordedBy",
    "DISTRIBUTED_BY": "DistributedBy",
    "COVER_OF": "CoverOf",
    "LYRICAL_REFERENCE_TO": "LyricalReferenceTo",
    "DIRECTLY_SAMPLES": "DirectlySamples",
    "MEMBER_OF": "MemberOf",
    "PRODUCER_OF": "ProducerOf",
}

DEFAULT_LABEL_PERSON = "Person"
DEFAULT_LABEL_SONG = "Song"
