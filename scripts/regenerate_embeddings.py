"""
重新生成知识库中所有文档的 embedding
用于修复之前 sync 时未生成 embedding 的问题
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.knowledge_base import get_knowledge_base
from app.config import POSTGRES_HOST, POSTGRES_DB
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def regenerate_embeddings():
    """重新生成所有文档的 embedding"""
    logger.info(f"连接数据库：{POSTGRES_HOST}/{POSTGRES_DB}")
    
    kb = get_knowledge_base()
    kb.initialize()
    
    # 获取所有 embedding 为 NULL 的记录
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=5432,
        database=POSTGRES_DB,
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
    
    # 查询所有需要处理的文件
    cur.execute("""
        SELECT DISTINCT file_name, file_path, COUNT(*) as chunk_count
        FROM document_chunks
        WHERE embedding IS NULL
        GROUP BY file_name, file_path
        ORDER BY file_name
    """)
    files = cur.fetchall()
    
    if not files:
        logger.info("所有文档已有 embedding，无需处理")
        return
    
    logger.info(f"发现 {len(files)} 个文件需要重新生成 embedding")
    
    total_chunks = 0
    processed_files = 0
    
    for file_name, file_path, chunk_count in files:
        logger.info(f"\n[{processed_files + 1}/{len(files)}] 处理：{file_name} ({chunk_count} chunks)")
        total_chunks += chunk_count
        
        try:
            # 查询该文件的所有 chunk
            cur.execute("""
                SELECT chunk_id, content, chunk_index
                FROM document_chunks
                WHERE file_name = %s AND embedding IS NULL
                ORDER BY chunk_index
            """, (file_name,))
            chunks = cur.fetchall()
            
            if not chunks:
                continue
            
            # 批量生成 embedding（每次最多 10 个，避免 API 限制）
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [chunk[1] for chunk in batch]
                
                logger.info(f"  生成 embedding 批次 {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")
                embeddings = kb._get_embedding_batch(texts)
                
                # 更新数据库
                for j, (chunk_id, content, chunk_index) in enumerate(batch):
                    embedding = embeddings[j]
                    if embedding is None:
                        logger.warning(f"  embedding 生成失败：{chunk_id}")
                        continue
                    
                    embedding_str = f"[{','.join(map(str, embedding))}]"
                    cur.execute("""
                        UPDATE document_chunks
                        SET embedding = %s::vector
                        WHERE chunk_id = %s
                    """, (embedding_str, chunk_id))
                
                conn.commit()
                logger.info(f"  批次 {i // batch_size + 1} 更新完成")
            
            processed_files += 1
            logger.info(f"✓ {file_name} 处理完成")
            
        except Exception as e:
            logger.error(f"✗ {file_name} 处理失败：{e}")
            conn.rollback()
    
    cur.close()
    conn.close()
    
    logger.info(f"\n========== 完成 ==========")
    logger.info(f"处理文件：{processed_files}/{len(files)}")
    logger.info(f"处理 chunks: {total_chunks}")
    logger.info(f"数据库：{POSTGRES_HOST}/{POSTGRES_DB}")


if __name__ == "__main__":
    regenerate_embeddings()
