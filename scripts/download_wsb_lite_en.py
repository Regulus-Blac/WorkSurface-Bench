"""Download Workspace-Bench-Lite English split from HuggingFace.

Only pulls the en subset + top-level metadata table. Skips the cn workspace
files (roughly halves the download) and the assets/ images.

Output:
  data/workspace-bench-lite-en/
    task_lite_clean_en/{task_id}/metadata.json
    task_lite_clean_en/{task_id}/data/*
    task_lite_clean_en_metadata_table.csv
    README.md
"""

import os
from huggingface_hub import snapshot_download

os.environ.setdefault("HTTP_PROXY", "http://hy-proxy.woa.com:3128")
os.environ.setdefault("HTTPS_PROXY", "http://hy-proxy.woa.com:3128")

REPO = "Workspace-Bench/Workspace-Bench-Lite"
LOCAL_DIR = "/apdcephfs_zwfy14/share_304380933/aldenliang/WorkSurface-Bench/data/workspace-bench-lite-en"

snapshot_download(
    repo_id=REPO,
    repo_type="dataset",
    local_dir=LOCAL_DIR,
    allow_patterns=[
        "task_lite_clean_en/**",
        "task_lite_clean_en_metadata_table.csv",
        "README.md",
    ],
    max_workers=8,
)

print(f"done -> {LOCAL_DIR}")
