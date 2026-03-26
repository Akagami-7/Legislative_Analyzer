import json
import os
from datetime import datetime
from codecarbon import EmissionsTracker

def log_compression(bill_id: str,
                    original_tokens: int,
                    compressed_tokens: int) -> dict:

    ratio = 1 - (compressed_tokens / max(original_tokens, 1))
    
    # Calculate content-only reduction for better clarity with small docs
    # (Assuming prompt overhead is roughly 300 tokens)
    estimated_overhead = 300
    content_tokens = max(0, compressed_tokens - estimated_overhead)
    content_ratio  = 1 - (content_tokens / max(original_tokens, 1))

    cost_naive       = round(original_tokens   * 0.000003, 4)
    cost_compressed  = round(compressed_tokens * 0.000003, 4)

    report = {
        "timestamp"          : datetime.now().isoformat(),
        "bill_id"            : bill_id,
        "original_tokens"    : original_tokens,
        "compressed_tokens"  : compressed_tokens,
        "reduction_percent"  : round(ratio * 100, 2),
        "content_reduction"  : round(content_ratio * 100, 2),
        "cost_naive_usd"     : cost_naive,
        "cost_compressed_usd": cost_compressed,
        "cost_saved_usd"     : round(cost_naive - cost_compressed, 4),
        "carbon_saved_grams" : round(ratio * 15, 2),  # fallback estimate
        "codecarbon_measured": False
    }

    log_path = f"compression_log_{bill_id}.json"
    with open(log_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*50)
    print("   TOKEN COMPRESSION REPORT")
    print("="*50)
    print(f"  Bill           : {bill_id}")
    print(f"  Original       : {original_tokens:,} tokens")
    print(f"  Compressed     : {compressed_tokens:,} tokens (Inc. prompt overhead)")
    print(f"  Content Redux  : {report['content_reduction']}% (Doc only)")
    print(f"  Total Redux    : {report['reduction_percent']}%")
    print(f"  Cost (naive)   : ${cost_naive}")
    print(f"  Cost (ours)    : ${cost_compressed}")
    print(f"  Saved          : ${report['cost_saved_usd']}")
    print(f"  CO2 saved      : {report['carbon_saved_grams']}g (estimated)")
    print("="*50)
    print(f"\n  Log saved to: {log_path}")
    return report


def track_pipeline_emissions(bill_id: str,
                              original_tokens: int,
                              compressed_tokens: int,
                              pipeline_fn,
                              *args, **kwargs):
    """
    Wraps any pipeline function with CodeCarbon tracking.
    Measures real emissions from running the compression.
    
    Usage:
        result = track_pipeline_emissions(
            bill_id, original_tokens, compressed_tokens,
            analyze_with_gemini, prompt, orig_tokens, comp_tokens
        )
    """
    tracker_started = False
    enabled = os.getenv("CODECARBON_ENABLED", "true").lower() == "true"
    
    if enabled:
        try:
            tracker = EmissionsTracker(
                project_name=f"legislative_analyzer_{bill_id}",
                output_dir=".",
                output_file=f"emissions_{bill_id}.csv",
                log_level="error",
                save_to_file=True,
                save_to_api=False
            )
            tracker.start()
            tracker_started = True
        except Exception as e:
            print(f"🌿 CodeCarbon: Hardware tracking disabled or failed ({str(e)}). Proceeding with estimate.")
    else:
        print(f"🌿 CodeCarbon: Tracking disabled via environment variable.")

    result = pipeline_fn(*args, **kwargs)

    if tracker_started:
        try:
            emissions_kg = tracker.stop()
        except:
            emissions_kg = None
    else:
        emissions_kg = None

    if emissions_kg is not None:
        emissions_grams   = round(emissions_kg * 1000, 4)
        ratio             = 1 - (compressed_tokens / max(original_tokens, 1))
        naive_emissions_g = round(emissions_grams / max(ratio, 0.01), 4)
        saved_grams       = round(naive_emissions_g - emissions_grams, 4)

        print(f"\n🌿 CodeCarbon measured:")
        print(f"   Actual emissions  : {emissions_grams}g CO2")
        print(f"   Naive would have  : {naive_emissions_g}g CO2")
        print(f"   Saved by compress : {saved_grams}g CO2")

        # Update the log file with real measurements
        log_path = f"compression_log_{bill_id}.json"
        if os.path.exists(log_path):
            with open(log_path) as f:
                report = json.load(f)

            report["codecarbon_measured"]      = True
            report["actual_emissions_grams"]   = emissions_grams
            report["naive_emissions_grams"]    = naive_emissions_g
            report["carbon_saved_grams_real"]  = saved_grams

            with open(log_path, "w") as f:
                json.dump(report, f, indent=2)

            print(f"   Log updated with real measurements")

    return result