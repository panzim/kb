## PEP 723 inline metadata ##
# /// script
# dependencies = [
#   "huggingface-hub",
# ]
# ///
from huggingface_hub import snapshot_download

# set HF_HOME before importing `transformers` or `sentence-transformers`
from pathlib import Path
import os
default_cache = Path(__file__).parent / "hf.cache"
os.environ.setdefault("HF_HOME", str(default_cache.absolute()))

# see document_loader.py - DocumentLoader.__init__
model_id = "sentence-transformers/all-mpnet-base-v2"

print(f"Downloading {model_id}...")
# This will download the model to the default HF cache directory
snapshot_download(repo_id=model_id,
  allow_patterns=["*.json", "flashrank*.onnx"],
  ignore_patterns=["*.bin", "*.safetensors"] # Skip the heavy weights
)
print("Download complete.")
