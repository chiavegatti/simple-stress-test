# Simple Stress Test

Small Python script to run a basic HTTP stress test against a URL.

## Requirements

- Python 3.8+
- requests

Install dependencies:

```bash
pip install -r requirements.txt
```

If you do not have a requirements file, install manually:

```bash
pip install requests
```

## Usage

```bash
python stress_test.py
```

You will be prompted for:

- URL
- Number of requests
- Number of threads
- Timeout in seconds (default 10)
- Number of repeats (default 1)
- HTTP method (GET/HEAD)
- Headers in JSON (optional)

## Output

The script writes two files under the output directory:

- output/report_<host>_<timestamp>.txt
- output/report_<host>_<timestamp>.json

The report includes URL, request count, thread count, totals, duration, and requests per second.

Additional metrics:

- Status distribution (200, 404, error, etc.)
- Latency min/avg/max (seconds)
- Per-run results and aggregate totals when repeats > 1

## Notes

- This is a simple test and does not replace a full load testing tool.
- Use with care on production systems.
