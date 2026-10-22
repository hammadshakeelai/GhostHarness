import os
import sys
import argparse
from pathlib import Path

def merge_lora_and_prepare(
    base_model_path: str,
    adapter_path: str,
    output_merged_path: str
):
    """
    Merges 4-bit LoRA adapter weights back into the base model
    producing a unified full checkpoint ready for llama.cpp GGUF conversion.
    """
    print("=" * 60)
    print(" GhostHarness: LoRA Adapter Merger")
    print(f" Base Model : {base_model_path}")
    print(f" Adapter    : {adapter_path}")
    print(f" Output     : {output_merged_path}")
    print("=" * 60)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("[ERROR] Requires torch, transformers, and peft.")
        sys.exit(1)

    print("[1/3] Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)

    print("[2/3] Merging LoRA adapter into base weights...")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    merged_model = model.merge_and_unload()

    print(f"[3/3] Saving merged model to {output_merged_path}...")
    merged_model.save_pretrained(output_merged_path)
    tokenizer.save_pretrained(output_merged_path)

    print("[SUCCESS] Model merged successfully!")
    print("To convert to GGUF for GhostHarness / LM Studio, run:")
    print(f"  python llama.cpp/convert_hf_to_gguf.py {output_merged_path} --outfile my_model_q4_k_m.gguf --outtype q4_k_m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LoRA into Base Model")
    parser.add_argument("--base", type=str, required=True, help="Base model path or HF ID")
    parser.add_argument("--adapter", type=str, required=True, help="LoRA adapter directory")
    parser.add_argument("--output", type=str, default="./merged_model", help="Merged output dir")
    args = parser.parse_args()

    merge_lora_and_prepare(args.base, args.adapter, args.output)
