"""Bounded CPU tensor process with controlled local assets, never arbitrary code."""

import json
import resource
import sys
import time


def main():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    from ml.pathable_ml.model import classify, load

    started = time.monotonic()
    if sys.argv[1] == "--validate":
        load(sys.argv[2])
        print('{"valid":true}')
    else:
        result = classify(sys.argv[1], sys.argv[2])
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"error_code":"INFERENCE_FAILED"}')
        sys.exit(1)
