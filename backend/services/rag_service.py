# 创建RAG知识库，以后AI发现问题时，通过检索RAG知识库找到解决案例
# 创建知识库用Chroma
"""
Chroma属性：
1. Client：客户端连接
2. Collection：创建知识库，类似于数据库create table
3. Document：知识库文本
4. Embedding：文本转换后的向量
5. Metadata：文本的属性
6. ID：知识库的记录ID
"""
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from typing import List, Dict, Optional

import chromadb

from services.embedding_service import EmbeddingService

"""
答题步骤：
1. 创建初始化，连接chroma，创建collection
2. index方法：
    （1）遍历alerts
    （2）每条：拼文本、记下ID、存元数据
    （3）批量转向量
    （4）村Chroma
3. search方法：
    （1）query转向量
    （2）调Chroma检索
    （3）整理返回
"""


# 一、创建初始化
class RagService:
    # 创建new方法
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # 创建持久化连接、目录、建立collection
    def _init(self):
        # 持久化目录
        p_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/data/chroma")
        os.makedirs(p_dir, exist_ok=True)

        # 创建持久化客户端
        self.client = chromadb.PersistentClient(path=p_dir)

        # 获取collection，创建collection
        self.connection = self.client.get_or_create_collection(
            name="ops_rag",
            metadata={"hnsw:space": "cosine"},  # 余弦相似度
        )

        # 调用向量服务
        self.embedding = EmbeddingService()

    # 二、接下来遍历alerts（告警），并进行向量转换、文本追加、元数据追加、存储chroma中
    """
    alerts大致情况
    [
            {
                'id': 123,
                'resource': 'CPU',
                'value': 95.2,
                'threshold': 80,
                'node': 'node1',
                'ai_advice': '...',
                'triggered_at': '2026-09-23 10:00:00',
                'resolved_at': '2026-09-23 10:30:00',
            },
            ...
        ]
    """

    def info_chroma(self, alerts: List[Dict]) -> Dict:
        # 创建向量、元数据、ID
        documents = []
        metadata = []
        ids = []

        # 判断alerts是否为空，空的话就返回
        if not alerts:
            return {"indexed": 0, "skipped": 0}

        # 对alerts遍历，并将传入到构建文本方法进行转换
        for a in alerts:
            # 只得到有解决事件的告警
            if not a.get('resolved_at'):
                continue
            # 构建知识文本
            # 将转换后的文本传递到documents中
            documents.append(self._build_text(a))
            # 追加id
            ids.append(f"alert-{a['id']}")
            # 追加元数据
            metadata.append({
                "source": "alert_history",
                "source_id": a['id'],
                "resource": a.get('resource', 'unknown'),
                "node": a.get('node', 'unknown'),
                "triggered_at": str(a.get('triggered_at', '')),
            })

        if not documents:
            return {"indexed": 0, "skipped": len(alerts)}

        # 向量转换
        embeder = self.embedding.embeds(documents)

        # 写入到chroma中，upsert有就更新，没有就创建，不然只用add更新会报错
        self.connection.upsert(
            ids=ids,
            metadatas=metadata,
            documents=documents,
            embeddings=embeder,
        )

        return {"indexed": len(documents), "skipped": len(alerts) - len(documents)}

    def _build_text(self, a):
        # 转换为通读文本
        parts = [
            f"资源类型：{a.get('resource', 'unknown')}",
            f"节点：{a.get('node', 'unknown')}",
            f"触发值：{a.get('value', '?')}%",
            f"告警阈值：{a.get('threshold', '?')}%",
            f"触发时间：{a.get('triggered_at', '')}",
            f"解决时间：{a.get('resolved_at', '')}",
        ]
        if a.get('ai_advice'):
            parts.append(f"AI 分析建议：{a['ai_advice']}")
        return "\n".join(parts)

    # 三、检索RAG知识库，什么思路：前端发送药检所的文本、条数、资源值（默认可不选）、最小匹配值，假设0.5，使用1-余弦值小于该值的检索就不用看了
    def search(self, query: str, top_k: int = 5, resource_filter: Optional[str] = None, th: float = 0.5):
        # 查看知识库是否为空
        if self.connection.count() == 0:
            return []

        # query转换向量
        query_em = self.embedding.embed(query)

        # 过滤资源值
        flag = None
        if resource_filter:
            flag = {'resource': resource_filter}

        # 返回检索值
        result = self.connection.query(
            query_embeddings=[query_em],
            n_results=top_k,
            where=flag,
        )

        """
        result大约参数：
            results = {
                'ids': [['alert-1', 'alert-5', 'alert-3', ...]],          # 二维列表
                'documents': [['资源类型：CPU\n节点：node1...', ...]],     # 二维列表
                'metadatas': [[{...}, {...}, ...]],                       # 二维列表
                'distances': [[0.12, 0.35, 0.48, ...]],                   # 二维列表
                'embeddings': None,   # 默认不返回
                'uris': None,
                'data': None,
                'included': ['metadatas', 'documents', 'distances'],
            }
        """

        # 捕获匹配值
        hit = []
        if not result['ids'] or not result['ids'][0]:
            return []

        # 遍历，查找余弦值进行相减
        for i, doc_id in enumerate(result['ids'][0]):
            dis = result['distances'][0][i] if result.get('distances') else 0
            # 'distances': [[0.12, 0.35, 0.48, ...]],
            # 距离相似值1-获得到的余弦值
            sum_si = 1 - dis
            # 耦合度小于0.5的就不用看了
            if sum_si < th:
                continue

            # 把检索的结果添加进去
            hit.append({
                'id': doc_id,
                'text': result['documents'][0][i],
                'metadata': result['metadatas'][0][i] if result.get('metadatas') else {},
                'similarity': round(sum_si, 3),
            })

        return hit

    # 四、辅助方法（统计RAG数量、清空RAG值）
    def count_RAG(self):
        return self.connection.count()

    # 删除
    def clear(self):
        """清空知识库"""
        self.client.delete_collection("ops_rag")
        self.connection = self.client.get_or_create_collection(
            name="ops_rag",
            metadata={"hnsw:space": "cosine"},
        )

