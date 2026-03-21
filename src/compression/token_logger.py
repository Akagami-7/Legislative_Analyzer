import json
from datetime import datetime

def log_compression(bill_id: str,
                    original_tokens: int,
                    compressed_tokens: int) -> dict:

    ratio = 1 - (compressed_tokens / max(original_tokens, 1))
    cost_naive      = round(original_tokens   * 0.000003, 4)
    cost_compressed = round(compressed_tokens * 0.000003, 4)

    report = {
        "timestamp"          : datetime.now().isoformat(),
        "bill_id"            : bill_id,
        "original_tokens"    : original_tokens,
        "compressed_tokens"  : compressed_tokens,
        "reduction_percent"  : round(ratio * 100, 2),
        "cost_naive_usd"     : cost_naive,
        "cost_compressed_usd": cost_compressed,
        "cost_saved_usd"     : round(cost_naive - cost_compressed, 4),
        "carbon_saved_grams" : round(ratio * 15, 2)
    }

    print("\n" + "=" * 50)
    print("   TOKEN COMPRESSION REPORT")
    print("=" * 50)
    print(f"  Bill           : {bill_id}")
    print(f"  Original       : {original_tokens:,} tokens")
    print(f"  Compressed     : {compressed_tokens:,} tokens")
    print(f"  Reduction      : {report['reduction_percent']}%")
    print(f"  Cost (naive)   : ${cost_naive}")
    print(f"  Cost (ours)    : ${cost_compressed}")
    print(f"  Saved          : ${report['cost_saved_usd']}")
    print(f"  CO2 saved      : {report['carbon_saved_grams']}g")
    print("=" * 50)

    log_path = f"compression_log_{bill_id}.json"
    with open(log_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Log saved to: {log_path}")
    return report