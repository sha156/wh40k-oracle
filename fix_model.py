import os
import requests
import zipfile

# 正确路径：prithivida/flashrank（flashrank 官方仓库）
model_name = "ms-marco-MiniLM-L-12-v2"
url = f"https://hf-mirror.com/prithivida/flashrank/resolve/main/{model_name}.zip"

cache_dir = "opt"
model_dir = os.path.join(cache_dir, model_name)
zip_path = os.path.join(cache_dir, f"{model_name}.zip")

# 准备目录
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
    print(f"📂 创建目录: {cache_dir}")

# 开始下载
print(f"🚀 正在从国内镜像下载高性能模型: {model_name}...")
print(f"🔗 地址: {url}")

try:
    response = requests.get(url, stream=True, proxies={"http": None, "https": None}, timeout=60)
    
    if response.status_code == 404:
        print("❌ 错误 404: 文件未找到。请检查模型名称和路径是否正确。")
        print("   当前地址:", url)
    else:
        response.raise_for_status()
        
        # 下载进度条（可选）
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r⬇️ 下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)
        print("\n✅ 下载完成！")

        # 解压
        print("📦 正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        
        print(f"🎉 成功！模型已保存到: {model_dir}")
        print("👉 在你的 app.py 或主程序中这样使用：")
        print("   from flashrank import Ranker")
        print(f"   ranker = Ranker(model_name=\"{model_name}\", cache_folder=\"opt\")")

except requests.exceptions.Timeout:
    print("❌ 下载超时，建议稍后重试或检查网络。")
except requests.exceptions.ConnectionError:
    print("❌ 连接失败，建议检查网络或更换镜像源。")
except Exception as e:
    print(f"❌ 下载或解压失败: {e}")
