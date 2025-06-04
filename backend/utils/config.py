from enum import Enum
from typing import Dict, Any

class VectorDBProvider(str, Enum):
    MILVUS = "milvus"
    CHROMA = "chroma"  # 新增 Chroma 支持
    # More providers can be added later

# 可以在这里添加其他配置相关的内容
MILVUS_CONFIG = {
    "uri": "03-vector-store/langchain_milvus.db",
    "index_types": {
        "flat": "FLAT",
        "ivf_flat": "IVF_FLAT",
        "ivf_sq8": "IVF_SQ8",
        "hnsw": "HNSW"
    },
    "index_params": {
        "flat": {},
        "ivf_flat": {"nlist": 1024},
        "ivf_sq8": {"nlist": 1024},
        "hnsw": {
            "M": 16,
            "efConstruction": 500
        }
    }
}

# Chroma 的配置
CHROMA_CONFIG = {
    "uri": "03-vector-store/chroma-data",  # 更新为本地路径
    "index_types": {
        "hnsw": "HNSW",  # 支持 HNSW 索引
        "standard": "STANDARD"  # 支持标准索引
    },
    "index_params": {
        "hnsw": {
            "M": 16,  # HNSW 参数
            "efConstruction": 200
        },
        "standard": {}  # 标准索引无额外参数
    }
} 