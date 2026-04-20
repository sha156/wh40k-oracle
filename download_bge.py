import os
from huggingface_hub import snapshot_download

# 设置镜像（无需代理）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 下载到自定义目录
cache_dir = "./opt/bge-small-zh-v1.5"
os.makedirs(cache_dir, exist_ok=True)

print("🚀 下载 BAAI/bge-small-zh-v1.5...")
snapshot_download(
    repo_id="BAAI/bge-small-zh-v1.5",
    cache_dir=cache_dir,
    local_dir_use_symlinks=False  # 确保完整复制
)

print(f"✅ 下载完成！模型保存到: {cache_dir}")
print("👉 在 app.py 中修改：model_name=\"./opt/bge-small-zh-v1.5\"")