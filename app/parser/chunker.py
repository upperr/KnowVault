"""
文本分块模块 - RAG 文档切片

实现常见的文本分块策略：
1. 按字符数分块（固定大小）
2. 带重叠的分块（保持上下文连续性）
3. 按段落/句子边界分块（保持语义完整性）
"""
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """文本片段"""
    content: str
    chunk_index: int
    total_chunks: int
    metadata: Dict = None


class TextChunker:
    """
    文本分块器
    
    分块策略：
    - 按字符数分块，但在段落/句子边界处切断
    - 相邻块之间有一定重叠，保持上下文连续性
    """
    
    # 默认配置（会被 config 中的值覆盖）
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    MIN_CHUNK_SIZE = 100
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        初始化分块器
        
        Args:
            chunk_size: 每个 chunk 的字符数
            chunk_overlap: 相邻 chunk 的重叠字符数
        """
        # 优先使用传入参数，其次使用 config 配置，最后使用默认值
        from app.config import CHUNK_SIZE, CHUNK_OVERLAP
        
        self.chunk_size = chunk_size if chunk_size is not None else CHUNK_SIZE
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP
        
        # 确保重叠不超过 chunk 大小
        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = self.chunk_size // 2
            logger.warning(f"chunk_overlap 调整为 {self.chunk_overlap}")
    
    def chunk_text(self, text: str, file_name: str = None) -> List[TextChunk]:
        """
        将文本分割为多个 chunk
        
        Args:
            text: 要分割的文本
            file_name: 文件名（用于日志）
            
        Returns:
            TextChunk 列表
        """
        if not text or not text.strip():
            return []
        
        # 如果文本很短，不需要分块
        if len(text) <= self.chunk_size:
            return [TextChunk(
                content=text.strip(),
                chunk_index=0,
                total_chunks=1,
                metadata={"file_name": file_name} if file_name else {}
            )]
        
        # 按段落分割
        paragraphs = self._split_by_paragraphs(text)
        
        # 合并段落为 chunks
        chunks = self._merge_paragraphs_to_chunks(paragraphs, file_name)
        
        logger.info(f"分块完成：{file_name or 'unknown'} -> {len(chunks)} 个 chunks")
        
        # 更新 total_chunks
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.total_chunks = total
            chunk.chunk_index = i
        
        return chunks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        按段落分割文本
        
        识别常见的段落分隔符：
        - 双换行符
        - Markdown 标题
        - 空行
        """
        paragraphs = []
        current_para = []
        
        lines = text.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # 空行表示段落结束
            if not stripped:
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
            else:
                current_para.append(line)
        
        # 处理最后一个段落
        if current_para:
            paragraphs.append('\n'.join(current_para))
        
        # 过滤空段落
        return [p for p in paragraphs if p.strip()]
    
    def _merge_paragraphs_to_chunks(self, paragraphs: List[str], file_name: str = None) -> List[TextChunk]:
        """
        将段落合并为 chunks
        
        策略：
        1. 尽量保持段落完整性
        2. 当累积文本超过 chunk_size 时，在段落边界处切断
        3. 添加重叠以保持上下文
        """
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # 如果单个段落就超过 chunk_size，需要进一步分割
            if para_length > self.chunk_size:
                # 先保存当前 chunk
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks), file_name))
                    current_chunk = []
                    current_length = 0
                
                # 分割长段落
                sub_chunks = self._split_long_paragraph(para)
                for sub_para in sub_chunks:
                    chunks.append(self._create_chunk([sub_para], len(chunks), file_name))
            
            # 如果添加这个段落会超过 chunk_size
            elif current_length + para_length > self.chunk_size:
                # 保存当前 chunk
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks), file_name))
                
                # 添加重叠部分
                overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)
                
                # 添加新段落
                current_chunk.append(para)
                current_length += para_length
            else:
                # 直接添加
                current_chunk.append(para)
                current_length += para_length
        
        # 处理最后一个 chunk
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, len(chunks), file_name))
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """
        分割过长的段落
        
        在句子边界处切断（句号、问号、感叹号等）
        """
        result = []
        
        # 按句子分割
        import re
        sentences = re.split(r'([.!?。！？；;])', paragraph)
        
        current_sentence = []
        current_length = 0
        
        for i, part in enumerate(sentences):
            if not part:
                continue
            
            part_length = len(part)
            
            # 如果是标点符号，直接添加到前一个句子
            if part in '.!?。！？；;':
                if current_sentence:
                    current_sentence.append(part)
                    current_length += 1
                continue
            
            # 如果添加这个句子会超过 chunk_size
            if current_length + part_length > self.chunk_size:
                # 保存当前 chunk
                if current_sentence:
                    result.append(''.join(current_sentence))
                
                current_sentence = [part]
                current_length = part_length
            else:
                current_sentence.append(part)
                current_length += part_length
        
        # 处理最后一个句子
        if current_sentence:
            result.append(''.join(current_sentence))
        
        # 如果还是太长，按固定长度分割
        final_result = []
        for text in result:
            if len(text) > self.chunk_size:
                for i in range(0, len(text), self.chunk_size):
                    final_result.append(text[i:i + self.chunk_size])
            else:
                final_result.append(text)
        
        return final_result
    
    def _create_chunk(self, lines: List[str], index: int, file_name: str = None) -> TextChunk:
        """创建 TextChunk 对象"""
        content = '\n'.join(lines).strip()
        return TextChunk(
            content=content,
            chunk_index=index,
            total_chunks=0,  # 会在后续更新
            metadata={"file_name": file_name} if file_name else {}
        )
    
    def _get_overlap_text(self, lines: List[str], overlap_size: int) -> str:
        """
        获取重叠文本
        
        从当前 chunk 的末尾提取 overlap_size 个字符作为下一个 chunk 的开头
        """
        if not lines:
            return ""
        
        # 从后往前累积文本，直到达到 overlap_size
        overlap_lines = []
        current_length = 0
        
        for line in reversed(lines):
            if current_length >= overlap_size:
                break
            overlap_lines.insert(0, line)
            current_length += len(line)
        
        return '\n'.join(overlap_lines) if overlap_lines else ""


def chunk_document(text: str, file_name: str = None, 
                   chunk_size: int = None, chunk_overlap: int = None) -> List[Dict]:
    """
    便捷函数：将文档分割为 chunks
    
    Args:
        text: 文档文本
        file_name: 文件名
        chunk_size: 每个 chunk 的字符数（默认使用 config 配置）
        chunk_overlap: 相邻 chunk 的重叠字符数（默认使用 config 配置）
        
    Returns:
        chunk 列表，每个 chunk 包含 content, chunk_index, total_chunks, metadata
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk_text(text, file_name)
    
    return [
        {
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "metadata": chunk.metadata or {}
        }
        for chunk in chunks
    ]
