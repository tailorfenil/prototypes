import argparse
import json
import random
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Any

from kafka import KafkaProducer


EVENT_TYPES = ["click", "view", "purchase", "login"]


@dataclass
class Event:
    event_id: str
    user_id: int
    event_time_ms: int
    ingest_time_ms: int
    event_type: str
    value: int
    partition_hint: str


def build_event(
    num_users: int,
    skew_mode: bool,
    late_event_ratio: float,
) -> Dict[str, Any]:
    now_ms = int(time.time() * 1000)

    # Skew mode simulates hot keys:
    # 80% traffic goes to a small hot set of users.
    if skew_mode and random.random() < 0.8:
        user_id = random.randint(1, min(5, num_users))
    else:
        user_id = random.randint(1, num_users)

    # Simulate late events by backdating event_time.
    event_time_ms = now_ms
    if random.random() < late_event_ratio:
        event_time_ms = now_ms - random.randint(5_000, 30_000)

    event = Event(
        event_id=str(uuid.uuid4()),
        user_id=user_id,
        event_time_ms=event_time_ms,
        ingest_time_ms=now_ms,
        event_type=random.choice(EVENT_TYPES),
        value=1,
        partition_hint=str(user_id),
    )
    return asdict(event)


def create_producer(bootstrap_servers: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8"),
        acks="all",
        retries=3,
        linger_ms=10,
    )


def run_producer(
    bootstrap_servers: str,
    topic: str,
    rate_per_sec: int,
    num_users: int,
    skew_mode: bool,
    late_event_ratio: float,
    burst_every_sec: int,
    burst_multiplier: int,
) -> None:
    producer = create_producer(bootstrap_servers)

    print("Starting producer with config:")
    print(
        json.dumps(
            {
                "bootstrap_servers": bootstrap_servers,
                "topic": topic,
                "rate_per_sec": rate_per_sec,
                "num_users": num_users,
                "skew_mode": skew_mode,
                "late_event_ratio": late_event_ratio,
                "burst_every_sec": burst_every_sec,
                "burst_multiplier": burst_multiplier,
            },
            indent=2,
        )
    )

    sent_count = 0
    start_time = time.time()
    window_start = start_time

    try:
        while True:
            elapsed = time.time() - start_time

            current_rate = rate_per_sec
            if burst_every_sec > 0 and int(elapsed) > 0 and int(elapsed) % burst_every_sec == 0:
                current_rate = rate_per_sec * burst_multiplier

            for _ in range(current_rate):
                event = build_event(
                    num_users=num_users,
                    skew_mode=skew_mode,
                    late_event_ratio=late_event_ratio,
                )

                # Key by user_id so Kafka partitioning is deterministic for the same key.
                future = producer.send(
                    topic,
                    key=event["user_id"],
                    value=event,
                )
                future.get(timeout=10)
                sent_count += 1

            producer.flush()

            now = time.time()
            if now - window_start >= 5:
                actual_rate = sent_count / (now - start_time)
                print(
                    f"[producer] total_sent={sent_count} "
                    f"avg_rate={actual_rate:.2f} events/sec"
                )
                window_start = now

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.flush()
        producer.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kafka event producer")
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default="events")
    parser.add_argument("--rate-per-sec", type=int, default=10)
    parser.add_argument("--num-users", type=int, default=100)
    parser.add_argument("--skew-mode", action="store_true")
    parser.add_argument("--late-event-ratio", type=float, default=0.0)
    parser.add_argument("--burst-every-sec", type=int, default=0)
    parser.add_argument("--burst-multiplier", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_producer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        rate_per_sec=args.rate_per_sec,
        num_users=args.num_users,
        skew_mode=args.skew_mode,
        late_event_ratio=args.late_event_ratio,
        burst_every_sec=args.burst_every_sec,
        burst_multiplier=args.burst_multiplier,
    )