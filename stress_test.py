import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

def stress_test(
    url,
    num_requests,
    num_threads,
    timeout=10.0,
    output_dir="output",
    repeats=1,
    method="GET",
    headers=None,
):
    local_state = threading.local()
    headers = headers or {}

    def get_session():
        if not hasattr(local_state, "session"):
            local_state.session = requests.Session()
        return local_state.session

    def make_request(request_url):
        start = time.perf_counter()
        status_code = None
        try:
            response = get_session().request(
                method,
                request_url,
                headers=headers,
                timeout=timeout,
            )
            status_code = response.status_code
        except requests.exceptions.RequestException:
            status_code = None
        duration = time.perf_counter() - start
        return status_code, duration

    def run_once(run_index):
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_request, url) for _ in range(num_requests)]
            results = [future.result() for future in futures]
        end_time = time.time()

        total_time = end_time - start_time
        status_counts = {}
        success_count = 0
        duration_sum = 0.0
        duration_count = 0
        duration_min = None
        duration_max = None

        for status, duration in results:
            duration_sum += duration
            duration_count += 1
            if duration_min is None or duration < duration_min:
                duration_min = duration
            if duration_max is None or duration > duration_max:
                duration_max = duration

            if status == 200:
                success_count += 1
            key = str(status) if status is not None else "error"
            status_counts[key] = status_counts.get(key, 0) + 1

        failed_count = len(results) - success_count
        requests_per_second = num_requests / total_time if total_time > 0 else 0.0
        duration_avg = duration_sum / duration_count if duration_count else 0.0

        report = {
            "run_index": run_index,
            "success_count": success_count,
            "failed_count": failed_count,
            "status_counts": status_counts,
            "total_time_seconds": round(total_time, 4),
            "requests_per_second": round(requests_per_second, 4),
            "latency_seconds": {
                "min": round(duration_min or 0.0, 6),
                "avg": round(duration_avg, 6),
                "max": round(duration_max or 0.0, 6),
            },
        }

        return report, duration_sum, duration_count, duration_min, duration_max, status_counts, total_time

    run_reports = []
    aggregate_status_counts = {}
    aggregate_success = 0
    aggregate_failed = 0
    aggregate_total_time = 0.0
    aggregate_duration_sum = 0.0
    aggregate_duration_count = 0
    aggregate_duration_min = None
    aggregate_duration_max = None

    for run_index in range(1, repeats + 1):
        (
            report,
            duration_sum,
            duration_count,
            duration_min,
            duration_max,
            status_counts,
            total_time,
        ) = run_once(run_index)

        run_reports.append(report)
        aggregate_success += report["success_count"]
        aggregate_failed += report["failed_count"]
        aggregate_total_time += total_time
        aggregate_duration_sum += duration_sum
        aggregate_duration_count += duration_count

        if duration_min is not None:
            aggregate_duration_min = (
                duration_min
                if aggregate_duration_min is None
                else min(aggregate_duration_min, duration_min)
            )
        if duration_max is not None:
            aggregate_duration_max = (
                duration_max
                if aggregate_duration_max is None
                else max(aggregate_duration_max, duration_max)
            )

        for key, value in status_counts.items():
            aggregate_status_counts[key] = aggregate_status_counts.get(key, 0) + value

    total_requests = num_requests * repeats
    aggregate_rps = (
        total_requests / aggregate_total_time if aggregate_total_time > 0 else 0.0
    )
    aggregate_latency_avg = (
        aggregate_duration_sum / aggregate_duration_count
        if aggregate_duration_count
        else 0.0
    )

    report = {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "url": url,
        "method": method,
        "headers": headers,
        "num_requests": num_requests,
        "num_threads": num_threads,
        "repeats": repeats,
        "timeout_seconds": timeout,
        "runs": run_reports,
        "aggregate": {
            "total_requests": total_requests,
            "success_count": aggregate_success,
            "failed_count": aggregate_failed,
            "status_counts": aggregate_status_counts,
            "total_time_seconds": round(aggregate_total_time, 4),
            "requests_per_second": round(aggregate_rps, 4),
            "latency_seconds": {
                "min": round(aggregate_duration_min or 0.0, 6),
                "avg": round(aggregate_latency_avg, 6),
                "max": round(aggregate_duration_max or 0.0, 6),
            },
        },
    }

    os.makedirs(output_dir, exist_ok=True)
    txt_path = os.path.join(output_dir, "report.txt")
    json_path = os.path.join(output_dir, "report.json")

    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(f"Timestamp (UTC): {report['timestamp_utc']}\n")
        txt_file.write(f"URL: {report['url']}\n")
        txt_file.write(f"Method: {report['method']}\n")
        txt_file.write(f"Headers: {json.dumps(report['headers'])}\n")
        txt_file.write(f"Requests per run: {report['num_requests']}\n")
        txt_file.write(f"Threads: {report['num_threads']}\n")
        txt_file.write(f"Repeats: {report['repeats']}\n")
        txt_file.write(f"Timeout (s): {report['timeout_seconds']}\n")
        txt_file.write("\nAggregate:\n")
        txt_file.write(
            f"  Total requests: {report['aggregate']['total_requests']}\n"
        )
        txt_file.write(
            f"  Successful requests: {report['aggregate']['success_count']}\n"
        )
        txt_file.write(f"  Failed requests: {report['aggregate']['failed_count']}\n")
        txt_file.write(
            f"  Status counts: {report['aggregate']['status_counts']}\n"
        )
        txt_file.write(
            f"  Total time: {report['aggregate']['total_time_seconds']} seconds\n"
        )
        txt_file.write(
            f"  Requests per second: {report['aggregate']['requests_per_second']}\n"
        )
        txt_file.write(
            "  Latency (s): min={min} avg={avg} max={max}\n".format(
                **report["aggregate"]["latency_seconds"]
            )
        )
        txt_file.write("\nRuns:\n")
        for run in report["runs"]:
            txt_file.write(f"  Run {run['run_index']}:\n")
            txt_file.write(f"    Successful requests: {run['success_count']}\n")
            txt_file.write(f"    Failed requests: {run['failed_count']}\n")
            txt_file.write(f"    Status counts: {run['status_counts']}\n")
            txt_file.write(f"    Total time: {run['total_time_seconds']} seconds\n")
            txt_file.write(
                f"    Requests per second: {run['requests_per_second']}\n"
            )
            txt_file.write(
                "    Latency (s): min={min} avg={avg} max={max}\n".format(
                    **run["latency_seconds"]
                )
            )

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(report, json_file, indent=2)

    print(f"Total requests: {report['aggregate']['total_requests']}")
    print(f"Successful requests: {report['aggregate']['success_count']}")
    print(f"Failed requests: {report['aggregate']['failed_count']}")
    print(f"Total time: {report['aggregate']['total_time_seconds']:.2f} seconds")
    print(
        f"Requests per second: {report['aggregate']['requests_per_second']:.2f}"
    )

if __name__ == "__main__":
    # Solicita os dados via prompts
    url = input("Informe a URL: ").strip()
    num_requests = int(input("Informe a quantidade de requests: "))
    num_threads = int(input("Informe a quantidade de threads: "))
    timeout_input = input("Informe o timeout em segundos (padrao 10): ").strip()
    repeats_input = input("Informe a quantidade de repeticoes (padrao 1): ").strip()
    method = input("Informe o metodo HTTP (GET/HEAD, padrao GET): ").strip().upper()
    headers_input = input("Informe headers em JSON (ou vazio): ").strip()

    if not url:
        raise SystemExit("URL invalida.")
    if num_requests <= 0 or num_threads <= 0:
        raise SystemExit("Numero de requests e threads deve ser maior que zero.")

    timeout = float(timeout_input) if timeout_input else 10.0
    repeats = int(repeats_input) if repeats_input else 1
    method = method or "GET"

    if timeout <= 0:
        raise SystemExit("Timeout deve ser maior que zero.")
    if repeats <= 0:
        raise SystemExit("Repeticoes deve ser maior que zero.")
    if method not in {"GET", "HEAD"}:
        raise SystemExit("Metodo HTTP invalido. Use GET ou HEAD.")

    headers = {}
    if headers_input:
        try:
            headers = json.loads(headers_input)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Headers em JSON invalidos: {exc}") from exc
        if not isinstance(headers, dict):
            raise SystemExit("Headers devem ser um objeto JSON.")

    # Executa o teste de stress
    stress_test(
        url,
        num_requests,
        num_threads,
        timeout=timeout,
        repeats=repeats,
        method=method,
        headers=headers,
    )
