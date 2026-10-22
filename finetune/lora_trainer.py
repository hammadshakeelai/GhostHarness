import os
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Force all HF & PyTorch caches into the USB repo folder
os.environ["HF_HOME"] = str(PROJECT_ROOT / ".cache" / "huggingface")
os.environ["TORCH_HOME"] = str(PROJECT_ROOT / ".cache" / "torch")

def train_qwen_qlora(
    dataset_path: str,
    base_model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    output_dir: str = str(PROJECT_ROOT / "finetune" / "adapters" / "default_lora"),
    max_seq_length: int = 2048,
    lora_r: int = 8,
    lora_alpha: int = 16,
    batch_size: int = 1,
    grad_accum: int = 8,
    epochs: int = 3
):
    """
    Fine-tunes Qwen 2.5 Coder on a 6GB VRAM discrete GPU using 4-bit QLoRA.
    Configured with gradient checkpointing, NF4 quantization, and minimal rank.
    """
    print("=" * 60)
    print(" GhostHarness: On-The-Go 6GB VRAM QLoRA Trainer")
    print(f" Target Model : {base_model_id}")
    print(f" Dataset      : {dataset_path}")
    print(f" VRAM Budget  : ~4.9 GB allocated / 6 GB capacity")
    print("=" * 60)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from datasets import load_dataset
        from trl import SFTTrainer
    except ImportError:
        print("[ERROR] Fine-tuning dependencies not installed.")
        print("Install user-space wheels with: pip install --user torch transformers peft bitsandbytes datasets trl")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("[ERROR] CUDA is not available on this system. Cannot utilize GPU.")
        sys.exit(1)

    device_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"[GPU DETECTED] {device_name} ({vram_total:.1f} GB total VRAM)")

    # 4-bit NF4 Quantization Configuration
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print("[1/4] Loading tokenizer & base model in 4-bit...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )

    print("[2/4] Preparing model for k-bit training with gradient checkpointing...")
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    # LoRA config targeted at attention projections
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("[3/4] Loading dataset from disk...")
    raw_dataset = load_dataset("json", data_files=dataset_path, split="train")

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        warmup_steps=10,
        num_train_epochs=epochs,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=5,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=raw_dataset,
        peft_config=lora_config,
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("[4/4] Starting training loop...")
    trainer.train()

    print(f"[SUCCESS] Training complete. Saving LoRA weights to: {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GhostHarness 6GB VRAM QLoRA Trainer")
    parser.add_argument("--dataset", type=str, required=True, help="Path to JSONL dataset")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct", help="Base HF Model")
    parser.add_argument("--output", type=str, default="./lora_adapter", help="Output directory")
    args = parser.parse_args()

    train_qwen_qlora(dataset_path=args.dataset, base_model_id=args.model, output_dir=args.output)
