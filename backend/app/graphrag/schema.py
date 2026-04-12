"""Graph schema constants and setup for Neo4j."""

# Node labels used in the graph
NODE_LABELS = [
    "Person",
    "Relationship",
    "Project",
    "Place",
    "Event",
    "Value",
    "Habit",
    "CommunicationPattern",
    "EmotionalTrigger",
    "Decision",
    "Situation",
    "Topic",
]

# Edge types
EDGE_TYPES = [
    "KNOWS",
    "WORKS_WITH",
    "RELATES_TO",
    "PARTICIPATES_IN",
    "VALUES",
    "TRIGGERS",
    "DECIDED",
    "LOCATED_AT",
    "PATTERN_OF",
    "LINKED_TO",
]

# Constraint / index creation Cypher (run once at startup)
SETUP_QUERIES = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.uid IS UNIQUE",
    "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.persona_id)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.type)",
]
