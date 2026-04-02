import tiktoken
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import BillSection, IngestedBill
from typing import List, Tuple

enc = tiktoken.get_encoding("cl100k_base")

TASK_INSTRUCTION = """
================================================
TASK: Analyze this bill for Indian citizens.
Return ONLY this JSON, no other text:
{
  "citizen_summary": "3 sentences, Grade 8 reading level, plain English",
  "key_changes": ["exactly 5 most impactful changes for ordinary citizens"],
  "affected_groups": ["list of citizens or sectors affected"],
  "rights_impact": "one sentence on fundamental rights implications",
  "implementation_date": "when this takes effect",
  "tokens_input": 0,
  "tokens_output": 0,
  "compression_ratio": 0.0,
  "carbon_saved_grams": 0.0
}
"""

TOKEN_CEILING = 15000

def build_prompt_text(bill: IngestedBill, sections: List[BillSection]) -> str:
    lines = []
    lines.append(f"BILL ID      : {bill.bill_id}")
    lines.append(f"SOURCE       : {bill.source_url}")
    lines.append(f"ORIGINAL SIZE: {bill.total_token_count:,} tokens")
    lines.append("=" * 60)

    for section in sections:
        lines.append(f"\n[{section.section_title.upper()}]")
        lines.append(section.section_text)

    return "\n".join(lines) + TASK_INSTRUCTION

def assemble_prompt(bill: IngestedBill,
                    compressed_sections: List[BillSection],
                    rag_context: str = "") -> Tuple[str, int]:

    lines = []
    lines.append(f"BILL ID      : {bill.bill_id}")
    lines.append(f"SOURCE       : {bill.source_url}")
    lines.append(f"ORIGINAL SIZE: {bill.total_token_count:,} tokens")
    lines.append("=" * 60)

    if rag_context:
        lines.append("\n" + rag_context)
        lines.append("=" * 60)

    for section in compressed_sections:
        section_text_block = f"\n[{section.section_title.upper()}]\n{section.section_text}"
        section_tokens = len(enc.encode(section_text_block))

        if len(enc.encode("\n".join(lines) + TASK_INSTRUCTION)) + section_tokens > TOKEN_CEILING:
            lines.append("\n[TRUNCATED: Document exceeds max length. Summarizing available sections.]\n")
            print(f"⚠️ Prompt reached ceiling ({TOKEN_CEILING} tokens). Truncating remaining sections.")
            break

        lines.append(section_text_block)

    context = "\n".join(lines)
    full_prompt = context + TASK_INSTRUCTION
    token_count = len(enc.encode(full_prompt))

    print(f"\n📝 Prompt assembled:")
    print(f"   Prompt tokens     : {token_count:,}")
    print(f"   Original tokens   : {bill.total_token_count:,}")
    print(f"   Compression ratio : "
          f"{(1 - token_count/bill.total_token_count)*100:.1f}%")

    return full_prompt, token_count
