import json

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors.kafka import KafkaSource
from pyflink.common.watermark_strategy import WatermarkStrategy

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream import CheckpointingMode

from pyflink.datastream.connectors.kafka import KafkaSink, KafkaRecordSerializationSchema

from pyflink.datastream.checkpoint_storage import FileSystemCheckpointStorage


from pyflink.common.typeinfo import Types


# ---------- Helper ----------
def parse_event(raw_str):
    try:
        return json.loads(raw_str)
    except Exception as e:
        return {"error": str(e), "raw": raw_str}


# ---------- Main ----------
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

# enable checkpointing
env.enable_checkpointing(10000)
env.get_checkpoint_config().set_checkpoint_storage(
    FileSystemCheckpointStorage("file:///tmp/flink-checkpoints")
)

checkpoint_config = env.get_checkpoint_config()
checkpoint_config.set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
checkpoint_config.set_min_pause_between_checkpoints(5000)
checkpoint_config.set_checkpoint_timeout(60000)
checkpoint_config.set_max_concurrent_checkpoints(1)


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


# Convert to JSON string with explicit type
to_json = parsed.map(
    lambda x: json.dumps(x),
    output_type=Types.STRING()
)


# Kafka Sink
sink = (
    KafkaSink.builder()
    .set_bootstrap_servers("kafka:9093")
    .set_record_serializer(
        KafkaRecordSerializationSchema.builder()
        .set_topic("events_parsed")
        .set_value_serialization_schema(SimpleStringSchema())
        .build()
    )
    .build()
)

# Write to Kafka
to_json.sink_to(sink)

# Execute
env.execute("Kafka → Flink DataStream Job")