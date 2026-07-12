#!/usr/bin/env python3
"""PostgreSQL + pgvector 连接测试"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test():
    try:
        import psycopg2
        from app.config import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST, port=POSTGRES_PORT,
            database=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD
        )
        cur = conn.cursor()
        
        # 检查 pgvector
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone():
            logger.info("✅ pgvector 扩展已安装")
        else:
            logger.error("❌ pgvector 未安装")
            return False
        
        # 检查表
        cur.execute("SELECT COUNT(*) FROM document_chunks")
        count = cur.fetchone()[0]
        logger.info(f"✅ 文档数量：{count}")
        
        cur.close()
        conn.close()
        logger.info("✅ PostgreSQL 连接测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if test() else 1)
