"""Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm.

Reduces a time series to at most n_out points while preserving visual shape.
No external dependencies required.
"""

from __future__ import annotations


def lttb(timestamps: list, values: list, n_out: int = 1000) -> tuple[list, list]:
    """Downsample (timestamps, values) to at most n_out points using LTTB.

    Returns a tuple (timestamps_out, values_out). If len(timestamps) <= n_out,
    the input is returned unchanged. None values are kept as-is (gaps preserved).
    """
    n = len(timestamps)
    if n <= n_out or n_out < 3:
        return timestamps, values

    result_ts: list = [timestamps[0]]
    result_v: list = [values[0]]

    # Split data (excluding first and last) into n_out - 2 equally spaced buckets
    bucket_size = (n - 2) / (n_out - 2)

    prev_idx = 0  # index of the last selected point

    for i in range(n_out - 2):
        # Determine bucket boundaries
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)

        # Compute average of the NEXT bucket (used as reference point)
        next_start = bucket_end
        next_end = min(int((i + 3) * bucket_size) + 1, n - 1)
        avg_ts, avg_v = _bucket_avg(timestamps, values, next_start, next_end)

        # Find the point in the current bucket that forms the largest triangle
        # with prev_idx point and the next-bucket average
        prev_ts_val = _to_numeric(timestamps[prev_idx])
        prev_v_val = values[prev_idx] if values[prev_idx] is not None else 0.0

        max_area = -1.0
        max_idx = bucket_start
        for j in range(bucket_start, bucket_end):
            area = _triangle_area(
                prev_ts_val,
                prev_v_val,
                _to_numeric(timestamps[j]),
                values[j] if values[j] is not None else 0.0,
                avg_ts,
                avg_v,
            )
            if area > max_area:
                max_area = area
                max_idx = j

        result_ts.append(timestamps[max_idx])
        result_v.append(values[max_idx])
        prev_idx = max_idx

    result_ts.append(timestamps[-1])
    result_v.append(values[-1])
    return result_ts, result_v


def _to_numeric(ts) -> float:
    """Convert a timestamp to a float for area calculations."""
    if hasattr(ts, "timestamp"):
        return ts.timestamp()
    try:
        return float(ts)
    except (TypeError, ValueError):
        return 0.0


def _bucket_avg(timestamps: list, values: list, start: int, end: int) -> tuple[float, float]:
    count = 0
    ts_sum = 0.0
    v_sum = 0.0
    for i in range(start, end):
        ts_sum += _to_numeric(timestamps[i])
        v = values[i]
        v_sum += v if v is not None else 0.0
        count += 1
    if count == 0:
        return 0.0, 0.0
    return ts_sum / count, v_sum / count


def _triangle_area(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float
) -> float:
    return abs((ax - cx) * (by - ay) - (ax - bx) * (cy - ay)) * 0.5
