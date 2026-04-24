from __future__ import annotations

from services.vision.realtime import (
    FrameSkippingConfig,
    FrameSkippingPolicy,
    LatestItemBuffer,
)


def test_latest_item_buffer_keeps_only_most_recent_packet() -> None:
    buffer: LatestItemBuffer[int] = LatestItemBuffer()

    buffer.put(1)
    buffer.put(2)
    buffer.put(3)

    assert buffer.get_latest(timeout=0.01) == 3
    assert buffer.get_latest(timeout=0.01) is None


def test_frame_skipping_policy_uses_hot_interval_under_high_cpu() -> None:
    policy = FrameSkippingPolicy(
        FrameSkippingConfig(
            base_interval=1,
            hot_interval=3,
            cpu_hot_threshold_percent=90,
        )
    )

    assert policy.should_process(frame_index=0, cpu_percent=95)
    assert not policy.should_process(frame_index=1, cpu_percent=95)
    assert not policy.should_process(frame_index=2, cpu_percent=95)
    assert policy.should_process(frame_index=3, cpu_percent=95)


def test_frame_skipping_policy_processes_every_frame_when_cpu_is_normal() -> None:
    policy = FrameSkippingPolicy(FrameSkippingConfig(base_interval=1, hot_interval=3))

    assert policy.should_process(frame_index=1, cpu_percent=30)
