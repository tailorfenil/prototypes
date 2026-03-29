import json

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors.kafka import KafkaSource
from pyflink.common.watermark_strategy import WatermarkStrategy


# ---------- Helper ----------
def parse_event(raw_str):
    try:
        return json.loads(raw_str)
    except Exception as e:
        return {"error": str(e), "raw": raw_str}


# ---------- Main ----------
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

# (we'll add checkpoints later)

# Kafka Source
source = (
    KafkaSource.builder()
    .set_bootstrap_servers("kafka:9093")   # IMPORTANT (docker)
    .set_topics("events")
    .set_group_id("flink-group")
    .set_value_only_deserializer(SimpleStringSchema())
    .build()
)

# Stream
stream = env.from_source(
    source,
    WatermarkStrategy.no_watermarks(),  # we’ll improve later
    "Kafka Source"
)

# Parse JSON
parsed = stream.map(parse_event)

# Print output
parsed.print()

# Execute
env.execute("Kafka → Flink DataStream Job")