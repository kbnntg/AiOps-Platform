# 把文本转为向量，找到各资源对应的向量区间，因为计算机无法通过文本来判断两种语句像不像，转换为向量好辨识
"""
"猫"   → [0.21, -0.53, 0.88, ..., 0.12]   # 768 维或 1536 维
"狗"   → [0.19, -0.48, 0.91, ..., 0.10]
"汽车" → [-0.72, 0.33, -0.15, ..., 0.67]

搜"重启容器" → 也能找到 "如何重新启动 Pod"、"restart deployment"
"""
import os
from typing import List

from openai import OpenAI

# RAG：定义一个知识库，让AI解决问题时提前往知识库中查找是否有历史案例
"""
典型案例：
【离线阶段】
文档1 → Embedding → [0.21, -0.53, ...] → 存入向量数据库
文档2 → Embedding → [0.18, -0.49, ...] → 存入向量数据库
文档3 → Embedding → [-0.72, 0.33, ...] → 存入向量数据库

【在线阶段】
用户提问："Pod 一直 Pending 怎么办"
         ↓
      Embedding
         ↓
   [0.20, -0.51, ...]
         ↓
   在向量数据库里找最相似的 Top 5
         ↓
   把这几段文档 + 用户问题一起喂给大模型
         ↓
   大模型基于真实文档生成回答
"""


# 一、定义类
class EmbeddingService:
    # 调用Embedding API把文本转为向量
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # 没有创建过实例就创建
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # 创建调用API所需属性
        self.api_key = os.getenv("EMBEDDING_API_KEY")
        self.base_url = os.getenv("EMBEDDING_API_URL", "https://api.siliconflow.cn/v1")
        self.model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
        # 创建AI
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    # 单条文本转向量（适用于文本不多情况）
    def embed(self, text: str) -> List[float]:
        # 判断是否有API_KEY
        if not self.api_key:
            raise RuntimeError("未配置API_KEY")
        resp = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        # 返回转换后的向量
        return resp.data[0].embedding

    # 多条文本转向量
    def embeds(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        # 飘零文本转向量
        if not self.api_key:
            raise RuntimeError("未配置 EMBEDDING_API_KEY")
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # 再次截断每条（保险）
            batch = [t[:400] for t in batch]
            try:
                resp = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                sorted_data = sorted(resp.data, key=lambda x: x.index)
                all_embeddings.extend([d.embedding for d in sorted_data])
            except Exception as e:
                print(f"批量 embedding 失败（批次 {i}）：{e}")
                # 降级：逐条调用，失败的用零向量占位
                for t in batch:
                    try:
                        r = self.client.embeddings.create(model=self.model, input=t[:400])
                        all_embeddings.append(r.data[0].embedding)
                    except Exception as e2:
                        print(f"单条 embedding 失败：{e2}")
                        # 用零向量占位，保证数量和输入一致
                        all_embeddings.append([0.0] * 1024)

        return all_embeddings
