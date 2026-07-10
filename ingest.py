"""
ingest.py — 战锤40K规则书知识库构建脚本
=========================================
功能：
  1. 扫描 data/ 目录下所有 PDF（支持中文文件名）
  2. 使用 PyMuPDFLoader 提取文本（速度快、支持中文）
  3. SemanticChunker 语义分块（比固定长度分块更智能）
  4. BAAI/bge-m3 嵌入（多语言、中英文混合效果最好）
  5. 构建 FAISS 向量库并保存到 local_vector_store/
  6. 每个 chunk 携带 source（文件路径）、book（书名）、page 元数据

使用：
  python ingest.py              # 增量构建（跳过已处理文件）
  python ingest.py --rebuild    # 清空重建
"""

import os
import re
import sys
import json
import shutil
import argparse
import time
import hashlib
import multiprocessing
from pathlib import Path

# ── CPU 并行：让 OpenMP / MKL / Torch 用满所有核心（必须在所有导入之前设置）──
_CPU_COUNT = str(multiprocessing.cpu_count())
os.environ.setdefault("OMP_NUM_THREADS",        _CPU_COUNT)
os.environ.setdefault("MKL_NUM_THREADS",        _CPU_COUNT)
os.environ.setdefault("OPENBLAS_NUM_THREADS",   _CPU_COUNT)
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", _CPU_COUNT)
os.environ.setdefault("NUMEXPR_NUM_THREADS",    _CPU_COUNT)

# ── 镜像 / 代理 设置（放在所有 HuggingFace 导入之前）──
os.environ["HF_ENDPOINT"]            = "https://hf-mirror.com"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HTTPS_PROXY"]            = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"]             = "http://127.0.0.1:7897"

# ── TLS 校验收窄（H8）：仅对 hf-mirror.com 关闭证书校验，其余请求保持正常校验 ──
# 此前是全进程禁用（ssl 默认上下文替换 + CURL_CA_BUNDLE/REQUESTS_CA_BUNDLE 置空 +
# 全局 verify=False），模型下载全程暴露于中间人攻击；现改为单 host 白名单。
from urllib.parse import urlparse

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_orig_request = requests.Session.request


def _is_hf_mirror_url(url: str) -> bool:
    """目标 host 是否为 hf-mirror.com（或其子域）——只有它才跳过证书校验。"""
    try:
        host = urlparse(str(url)).hostname or ""
    except ValueError:
        return False
    return host == "hf-mirror.com" or host.endswith(".hf-mirror.com")


def _hf_mirror_request(self, method, url, **kwargs):
    if _is_hf_mirror_url(url):
        kwargs.setdefault("verify", False)
    return _orig_request(self, method, url, **kwargs)


requests.Session.request = _hf_mirror_request
print("⚠️  已对 hf-mirror.com 关闭 TLS 证书校验（其余请求保持正常校验）")

from tqdm import tqdm
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from corpus_manifest import classify_book, load_manifest
from hf_embeddings_compat import build_huggingface_embeddings
from md_chunker import load_refined_book

# ══════════════════════════════════════════════
#  配置区（按需修改）
# ══════════════════════════════════════════════
DATA_DIR          = Path("data")                    # PDF 存放目录
VECTOR_STORE_PATH = Path("local_vector_store")      # FAISS 输出目录
PROCESSED_LOG     = Path("local_vector_store/processed_files.json")  # 增量记录
REFINED_DIR       = Path("data_refined")            # llm_refine.py 输出目录，存在则优先使用
MANIFEST_PATH     = Path("corpus_manifest.json")    # 书名→edition/layer 层级清单（11版迁移S1）

# 嵌入模型：bge-m3 中英文混合最强，本地加载
EMBED_MODEL_NAME  = "BAAI/bge-m3"
EMBED_MODEL_CACHE = "./opt"                         # 模型缓存目录

# SemanticChunker 断点类型：
#   "percentile"   — 按相似度百分位数分块（推荐，自适应）
#   "standard_deviation" — 标准差
#   "interquartile"      — 四分位距
BREAKPOINT_TYPE       = "percentile"
BREAKPOINT_THRESHOLD  = 85   # 百分位阈值，越大分块越少越大

# 嵌入 batch_size：CPU 核心数越多可适当调大，提升吞吐
EMBED_BATCH_SIZE = max(32, multiprocessing.cpu_count() * 4)


def parse_args():
    parser = argparse.ArgumentParser(description="构建战锤40K规则书向量知识库")
    parser.add_argument("--rebuild", action="store_true",
                        help="清空旧索引，从头重建")
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR),
                        help="PDF 文件夹路径")
    parser.add_argument("--no-blacklibrary", action="store_true",
                        help="不把黑图书馆中文 datasheet 注入 L1 检索层")
    return parser.parse_args()


def load_processed_log() -> dict:
    """读取已处理文件记录（文件名 → mtime），用于增量跳过。"""
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_processed_log(log: dict):
    """保存已处理文件记录。"""
    PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# 只从**结尾**剥离的版本/日期/汉化组噪声（顺序不敏感，多轮迭代剥净）。
# 关键：绝不在文件名**中间**的数字处截断——旧策略「取第一个数字之前」会把
# 『6月4日分数中文』『6月4日平衡版中午』都截成『6月』、把『钛帝国十版CODEX-20251112』
# 截成『钛帝国十版CODEX-』，导致不同书并成一个 book 名、引用与书目过滤失真。
_BOOK_TAIL_PATTERNS = [
    r"[Vv]?\d+(?:\.\d+)+$",            # 版本号 1.12 / V1.20 / 2.81
    r"CODEX[-\s]*\d{6,8}$",            # CODEX-20251112
    r"[-\s]*\d{6,8}$",                # 结尾 8 位日期
    r"CODEX[-\s]*$",                  # 剥掉版本后残留的 CODEX-
    r"(?:老湿腐版|DavidZ版|双子星版|双子星|kasa版?|官方版?)$",
    r"[Vv]\d+$",                      # 单独 V20 之类
    r"\s+\d+$",                       # 结尾空格+数字（如 '… 1'）
]


def get_book_name(filepath: Path) -> str:
    """从文件名提取「书名」元数据，只剥结尾的版本/日期/汉化组噪声，保证不同书不撞名。

    例：'黑暗天使10版中文老湿腐版1.12.pdf' → '黑暗天使10版中文'；
        '钛帝国十版CODEX-20251112.pdf' → '钛帝国十版'；
        '6月4日分数中文' / '6月4日平衡版中午' → 各自保留（不再并成 '6月'）。
    结果为空则回退完整文件名，避免 book="" 导致引用/过滤失效。
    """
    name = filepath.stem
    for _ in range(4):  # 多轮：版本号 + 汉化组 + 残留 CODEX 可能叠加
        before = name
        for pat in _BOOK_TAIL_PATTERNS:
            name = re.sub(pat, "", name, flags=re.IGNORECASE).strip(" -_")
        if name == before:
            break
    return name if name else filepath.stem


def refined_fingerprint(pdf_path: Path) -> str:
    """重构目录指纹：data_refined/<书名>/ 下所有 *.md 的 (文件名, mtime) 哈希；无目录/无文件返回 'none'。"""
    book_dir = REFINED_DIR / pdf_path.stem
    md_files = sorted(book_dir.glob("*.md"))
    if not md_files:
        return "none"
    h = hashlib.sha256()
    for f in md_files:
        h.update("{}:{}".format(f.name, os.path.getmtime(f)).encode("utf-8"))
    return h.hexdigest()[:16]


def load_pdf(pdf_path: Path) -> list[Document]:
    """
    加载单个 PDF，返回 Document 列表。
    每页一个 Document，元数据包含 source、book、page。
    """
    loader = PyMuPDFLoader(str(pdf_path))
    pages = loader.load()

    book_name = get_book_name(pdf_path)
    for doc in pages:
        doc.metadata["source"] = str(pdf_path)
        doc.metadata["book"]   = book_name
        # PyMuPDFLoader 的 page 元数据是 0 起始（C1）；统一为 1-based，
        # 与 llm_refine.py extract_pages 的 "page": i + 1 约定对齐——
        # 否则未走 refined 管线的书，引用里"第X页"全部比实际少 1。
        doc.metadata["page"] = int(doc.metadata.get("page", 0)) + 1

    return pages


def semantic_chunk(docs: list[Document], embeddings) -> list[Document]:
    """
    使用 SemanticChunker 对文档进行语义分块。
    按 source 分组处理，保持元数据不混淆。
    每本书处理时显示 tqdm 进度条。
    """
    from collections import defaultdict

    grouped: dict[str, list[Document]] = defaultdict(list)
    for doc in docs:
        grouped[doc.metadata["source"]].append(doc)

    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type=BREAKPOINT_TYPE,
        breakpoint_threshold_amount=BREAKPOINT_THRESHOLD,
    )

    all_chunks = []
    for source, source_docs in tqdm(grouped.items(),
                                    desc="  语义分块",
                                    unit="书",
                                    leave=False):
        base_meta = source_docs[0].metadata.copy()
        try:
            chunks = splitter.split_documents(source_docs)
        except Exception as e:
            tqdm.write(f"  ⚠️  语义分块失败 ({source})，回退到原始页面: {e}")
            chunks = source_docs

        for chunk in chunks:
            chunk.metadata.setdefault("source", base_meta.get("source", source))
            chunk.metadata.setdefault("book",   base_meta.get("book", "未知"))

        all_chunks.extend(chunks)

    return all_chunks


def build_embeddings():
    """初始化 BGE-M3 嵌入模型（本地加载，无需联网）。"""
    print(f"📡 加载嵌入模型: {EMBED_MODEL_NAME} ...")
    print(f"   CPU 核心数: {multiprocessing.cpu_count()}，batch_size: {EMBED_BATCH_SIZE}")
    embeddings = build_huggingface_embeddings(
        model_name=EMBED_MODEL_NAME,
        cache_folder=EMBED_MODEL_CACHE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": EMBED_BATCH_SIZE,
        },
    )
    print("✅ 嵌入模型加载完毕")
    return embeddings


def build_faiss_with_progress(chunks: list[Document], embeddings) -> FAISS:
    """
    逐批对 chunks 编码并构建 FAISS，附带 tqdm 进度条。
    比直接调用 FAISS.from_documents 多了可视化进度。
    """
    from langchain_community.vectorstores.utils import DistanceStrategy

    texts    = [c.page_content for c in chunks]
    metas    = [c.metadata for c in chunks]
    vectors  = []

    # sentence-transformers 内部也分批，这里再包一层显示总进度
    batch = EMBED_BATCH_SIZE
    with tqdm(total=len(texts), desc="  向量编码", unit="chunk") as pbar:
        for i in range(0, len(texts), batch):
            batch_texts = texts[i : i + batch]
            vecs = embeddings.embed_documents(batch_texts)
            vectors.extend(vecs)
            pbar.update(len(batch_texts))

    # 用 FAISS.from_embeddings 直接接收已算好的向量，避免二次编码
    text_embedding_pairs = list(zip(texts, vectors))
    store = FAISS.from_embeddings(
        text_embeddings=text_embedding_pairs,
        embedding=embeddings,
        metadatas=metas,
    )
    return store


def delete_stale_chunks(store, sources: set) -> int:
    """增量合并前，从已有索引删除 metadata['source'] 命中 sources 的旧 chunk（H3）。

    不删的话，文件变化重入库时新旧 chunk 并存、内容互相矛盾。返回删除数。
    """
    stale_ids = [doc_id for doc_id, doc in store.docstore._dict.items()
                 if doc.metadata.get("source") in sources]
    if stale_ids:
        store.delete(stale_ids)
    return len(stale_ids)


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)

    print("=" * 60)
    print("⚔️  战锤40K 规则书知识库构建器")
    print("=" * 60)

    # ── 清空重建 ──
    if args.rebuild and VECTOR_STORE_PATH.exists():
        print("🗑️  清空旧索引...")
        shutil.rmtree(VECTOR_STORE_PATH)

    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    # ── 扫描 PDF ──
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ 在 {data_dir} 目录下未找到任何 PDF 文件")
        sys.exit(1)

    print(f"\n📚 发现 {len(pdf_files)} 个 PDF 文件")

    # ── 增量过滤 ──
    processed_log = {} if args.rebuild else load_processed_log()
    to_process = []
    for pdf in pdf_files:
        mtime = "{}|{}".format(os.path.getmtime(pdf), refined_fingerprint(pdf))
        if processed_log.get(str(pdf)) == mtime:
            print(f"  ⏭️  跳过（已处理）: {pdf.name}")
        else:
            to_process.append(pdf)

    if not to_process:
        print("\n✅ 所有文件均已处理，无需重建。使用 --rebuild 强制重建。")
        return

    print(f"\n🔄 待处理: {len(to_process)} 个文件\n")

    # ── 加载嵌入模型 ──
    embeddings = build_embeddings()

    # ── 语料层级清单（11版迁移S1）：书名 → edition/layer ──
    manifest = load_manifest(MANIFEST_PATH)
    layer_stats: dict[str, int] = {}

    # ── 逐文件加载并累积 chunks ──
    all_new_chunks: list[Document] = []
    failed_files = []

    file_bar = tqdm(to_process, desc="📖 处理 PDF", unit="文件")
    for pdf_path in file_bar:
        file_bar.set_postfix(file=pdf_path.name[:30])
        t0 = time.time()

        try:
            base_meta = {"source": str(pdf_path), "book": get_book_name(pdf_path)}
            refined = load_refined_book(pdf_path, REFINED_DIR, base_meta)

            if refined is not None:
                chunks = refined
                tqdm.write(f"  🧩 {pdf_path.name}: 使用 LLM 重构结果，"
                           f"{len(chunks)} 个条目 chunk")
            else:
                pages = load_pdf(pdf_path)
                pages = [p for p in pages if len(p.page_content.strip()) > 20]

                if not pages:
                    tqdm.write(f"  ⚠️  {pdf_path.name}: 无可提取文本（扫描版），已跳过")
                    failed_files.append((pdf_path.name, "无文本层"))
                    continue

                tqdm.write(f"  📄 {pdf_path.name}: {len(pages)} 页")

                chunks = semantic_chunk(pages, embeddings)
                tqdm.write(f"  ✂️  分块完成: {len(chunks)} chunks  ({time.time()-t0:.1f}s)")

            tag = classify_book(base_meta["book"], manifest)
            for c in chunks:
                c.metadata.update(tag)
            key = "{}版/{}".format(tag["edition"], tag["layer"])
            layer_stats[key] = layer_stats.get(key, 0) + len(chunks)
            tqdm.write(f"  🏷️  {base_meta['book']} → {key}")

            all_new_chunks.extend(chunks)
            processed_log[str(pdf_path)] = "{}|{}".format(
                os.path.getmtime(pdf_path), refined_fingerprint(pdf_path))

        except Exception as e:
            tqdm.write(f"  ❌ {pdf_path.name} 处理失败: {e}")
            failed_files.append((pdf_path.name, str(e)))

    # ── 注入黑图书馆中文原生 datasheet（属性+能力全文+武器）到 L1 检索层 ──
    # 仅全量重建时注入（增量会重复）；黑图书馆随 db_compile 刷新，靠 --rebuild 同步。
    if args.rebuild and not args.no_blacklibrary:
        try:
            from agent.tools import DB_PATH as _DB
            from db_compile.blacklibrary import build_blacklibrary_docs
            hb_docs = build_blacklibrary_docs(_DB)
            if hb_docs:
                hb_tag = classify_book("黑图书馆", manifest)
                hb_key = "{}版/{}".format(hb_tag["edition"], hb_tag["layer"])
                for d in hb_docs:
                    d.metadata.update(hb_tag)
                layer_stats[hb_key] = layer_stats.get(hb_key, 0) + len(hb_docs)
                all_new_chunks.extend(hb_docs)
                print(f"  🐍 注入黑图书馆检索条目: {len(hb_docs)}")
            else:
                print("  ⚠️ 黑图书馆无数据（unit_zh_detail 空），跳过注入")
        except Exception as e:
            print(f"  ⚠️ 黑图书馆注入失败（跳过，不影响 PDF 索引）: {e}")

    if not all_new_chunks:
        print("\n❌ 没有生成任何有效 chunks，退出。")
        sys.exit(1)

    print(f"\n📊 总计 chunks: {len(all_new_chunks)}")
    print("📊 分层构成（edition/layer）:")
    for key in sorted(layer_stats):
        print(f"    {key}: {layer_stats[key]} chunks")

    # ── 构建 / 合并 FAISS（带进度条）──
    faiss_index_file = VECTOR_STORE_PATH / "index.faiss"

    print("\n🧠 构建向量索引...")
    t0 = time.time()

    if faiss_index_file.exists() and not args.rebuild:
        print("  ♻️  加载已有索引，执行增量合并...")
        existing_store = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        # ── 增量去重（H3）：先按 source 删除本次重新处理文件的旧 chunk 再合并，
        #    只删「本次已成功产出新 chunk」的来源，处理失败的文件保留旧数据 ──
        new_sources = {c.metadata.get("source") for c in all_new_chunks}
        new_sources.discard(None)
        removed = delete_stale_chunks(existing_store, new_sources)
        print(f"  🧹 增量去重：删除旧 chunk {removed} 个"
              f"（覆盖 {len(new_sources)} 个重处理来源）")
        new_store = build_faiss_with_progress(all_new_chunks, embeddings)

        # 维度校验：旧索引与新向量维度不一致时自动重建
        old_dim = existing_store.index.d
        new_dim = new_store.index.d
        if old_dim != new_dim:
            print(f"  ⚠️  维度不匹配（旧={old_dim}, 新={new_dim}），自动全量重建...")
            # 把已有 docstore 中的文档也重新编码
            old_docs = list(existing_store.docstore._dict.values())
            all_docs_combined = old_docs + all_new_chunks
            new_store = build_faiss_with_progress(all_docs_combined, embeddings)
            new_store.save_local(str(VECTOR_STORE_PATH))
        else:
            existing_store.merge_from(new_store)
            existing_store.save_local(str(VECTOR_STORE_PATH))
    else:
        vectorstore = build_faiss_with_progress(all_new_chunks, embeddings)
        vectorstore.save_local(str(VECTOR_STORE_PATH))

    print(f"✅ 向量索引保存完毕  ({time.time()-t0:.1f}s)")
    save_processed_log(processed_log)

    # ── 汇总报告 ──
    print("\n" + "=" * 60)
    print("📋 构建报告")
    print("=" * 60)
    print(f"  成功处理: {len(to_process) - len(failed_files)} / {len(to_process)} 个文件")
    print(f"  总 chunks: {len(all_new_chunks)}")
    print(f"  索引路径: {VECTOR_STORE_PATH.resolve()}")

    if failed_files:
        print(f"\n⚠️  失败文件 ({len(failed_files)}):")
        for name, reason in failed_files:
            print(f"    - {name}: {reason}")

    print("\n🎉 知识库构建完成！现在可以运行 .\\.venv\\Scripts\\streamlit.exe run app.py")


if __name__ == "__main__":
    main()
