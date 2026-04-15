from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class HiddenStateExtractorConfig:
    model_path: str
    device: str = "auto"
    dtype: str = "auto"
    max_length: int = 4096


class HiddenStateExtractor:
    def __init__(self, config: HiddenStateExtractorConfig):
        self.config = config
        # Resolve runtime device once so later inference stays consistent.
        self.device = self._resolve_device(config.device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            config.model_path,
            trust_remote_code=False,
            use_fast=True,
        )

        torch_dtype = self._resolve_dtype(config.dtype)
        model_kwargs = {
            "trust_remote_code": False,
            "output_hidden_states": True,
        }
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype

        self.model = AutoModelForCausalLM.from_pretrained(
            config.model_path, **model_kwargs
        )
        self.model.to(self.device)
        self.model.eval()

    def _resolve_device(self, device_name: str) -> str:
        if device_name == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device_name

    def _resolve_dtype(self, dtype_name: str):
        if dtype_name == "auto":
            return None
        mapping = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        if dtype_name not in mapping:
            raise ValueError(f"Unsupported dtype: {dtype_name}")
        return mapping[dtype_name]

    def render_messages(self, messages: Sequence[Dict[str, str]]) -> str:
        # Prefer model-native chat template for stable token alignment.
        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )

        # Fallback formatter if tokenizer has no chat template support.
        lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            lines.append(f"[{role}]\n{content}")
        lines.append("[ASSISTANT]\n")
        return "\n\n".join(lines)

    def extract_from_text(
        self,
        text: str,
        layer_indices: Optional[Sequence[int]] = None,
    ) -> Dict:
        # Keep offsets for char->token span projection used by anchor extraction.
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_length,
            return_offsets_mapping=True,
        )

        offset_mapping = encoded.pop("offset_mapping", None)
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        # Forward pass only, no KV cache needed for probing features.
        with torch.no_grad():
            outputs = self.model(
                **encoded,
                output_hidden_states=True,
                use_cache=False,
                return_dict=True,
            )

        hidden_states = outputs.hidden_states
        if hidden_states is None:
            raise RuntimeError("Model did not return hidden_states")

        num_layers = len(hidden_states) - 1
        # Layer 0 is embeddings; probing layers are 1..num_layers.
        if layer_indices is None:
            picked_layers = list(range(1, num_layers + 1))
        else:
            picked_layers = []
            for idx in layer_indices:
                # Support Python-style negative layer indices.
                if idx < 0:
                    idx = num_layers + 1 + idx
                if idx <= 0 or idx > num_layers:
                    raise ValueError(
                        f"Invalid layer index {idx}. Valid range: [1, {num_layers}]"
                    )
                picked_layers.append(idx)

        layer_hidden = {
            layer: hidden_states[layer][0].detach().cpu().to(torch.float32)
            for layer in picked_layers
        }

        token_ids = encoded["input_ids"][0].detach().cpu().tolist()
        attention_mask = encoded["attention_mask"][0].detach().cpu().tolist()
        if offset_mapping is None:
            offsets = []
        elif hasattr(offset_mapping, "detach"):
            offsets = offset_mapping[0].detach().cpu().tolist()
        else:
            offsets = offset_mapping[0]

        return {
            "token_ids": token_ids,
            "attention_mask": attention_mask,
            "offset_mapping": offsets,
            "layer_hidden": layer_hidden,
            "num_layers": num_layers,
        }
