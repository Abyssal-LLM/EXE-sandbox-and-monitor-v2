"""
T5+LoRA model wrapper for explaining sandbox log lines.
Loads the trained LoRA adapter on top of T5-small and provides
a simple explain() method that translates log lines to English.
"""
import sys
import threading
from pathlib import Path
from typing import Optional


def _log(msg: str) -> None:
    try:
        print(msg)
    except OSError:
        pass


class ModelExplainer:
    """
    Wraps a T5-small + LoRA model for log line explanation.

    Usage:
        explainer = ModelExplainer()
        explainer.load()  # call once at startup
        explanation = explainer.explain("[12:34:56.789] [FILE] notepad.exe(1234) CREATE: ...")
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._device = None
        self._loaded = False
        self._loading = False
        self._load_error = None
        self._lock = threading.Lock()

        # Resolve adapter path relative to the sandbox package
        self._adapter_path = (
            Path(__file__).resolve().parent.parent / "model" / "lora_adapter"
        )
        self._base_model = "t5-small"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def load(self) -> bool:
        """
        Load the base T5 model and apply the LoRA adapter.
        Safe to call from any thread — blocks until done.
        Returns True on success.
        """
        if self._loaded:
            return True
        if self._loading:
            return False

        self._loading = True
        self._load_error = None

        try:
            import torch
            from transformers import AutoTokenizer, T5ForConditionalGeneration
            from peft import PeftModel

            device = "cuda" if torch.cuda.is_available() else "cpu"

            _log(f"[ModelExplainer] Loading base model: {self._base_model}")
            tokenizer = AutoTokenizer.from_pretrained(self._base_model)

            if device == "cuda":
                model = T5ForConditionalGeneration.from_pretrained(
                    self._base_model,
                    torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
                    device_map="auto",
                )
            else:
                model = T5ForConditionalGeneration.from_pretrained(self._base_model)

            _log(f"[ModelExplainer] Applying LoRA adapter from: {self._adapter_path}")
            model = PeftModel.from_pretrained(model, str(self._adapter_path))
            model.eval()

            if device == "cpu":
                model = model.to(device)

            self._model = model
            self._tokenizer = tokenizer
            self._device = device
            self._loaded = True
            _log(f"[ModelExplainer] Model loaded on {device}")
            return True

        except Exception as e:
            self._load_error = str(e)
            try:
                print(f"[ModelExplainer] Failed to load model: {e}", file=sys.stderr)
            except OSError:
                pass
            return False

        finally:
            self._loading = False

    def explain(self, log_line: str) -> str:
        """
        Generate a human-readable explanation for a sandbox log line.
        Thread-safe: concurrent calls are serialized via a lock.

        Parameters:
            log_line: Raw log line from the terminal.

        Returns:
            English explanation, or a fallback message on error.
        """
        if not self._loaded:
            return "[Model not loaded]"
        if not log_line or not log_line.strip():
            return "[Empty line]"

        with self._lock:
            try:
                import torch

                prefix = "translate sandbox log to English: "
                inputs = self._tokenizer(
                    prefix + log_line,
                    return_tensors="pt",
                    max_length=256,
                    truncation=True,
                ).to(self._device)

                with torch.no_grad():
                    generated = self._model.generate(
                        **inputs,
                        max_length=128,
                        num_beams=4,
                        early_stopping=True,
                    )

                output = self._tokenizer.decode(generated[0], skip_special_tokens=True)
                return output.strip() if output.strip() else "[No explanation generated]"

            except Exception as e:
                return f"[Model error: {e}]"
