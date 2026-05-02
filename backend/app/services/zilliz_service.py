from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility, Function, FunctionType
from app.core.config import settings
from loguru import logger

class ZillizService:
    def __init__(self):
        self.collection_name = "portfolio_images"
        self.connected = False
        
    def connect(self):
        if not settings.zilliz_cloud_uri or not settings.zilliz_cloud_token:
            logger.warning("Zilliz Cloud config missing. Vector DB operations skipped.")
            return False
            
        try:
            connections.connect(
                alias="default",
                uri=settings.zilliz_cloud_uri,
                token=settings.zilliz_cloud_token
            )
            self.connected = True
            self._ensure_collection()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Zilliz: {e}")
            return False

    def _ensure_collection(self):
        if not utility.has_collection(self.collection_name):
            fields = [
                FieldSchema(name="image_id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="image_url", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000, enable_analyzer=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
                FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR)
            ]
            schema = CollectionSchema(fields, description="Portfolio Image Embeddings with BM25")
            
            bm25_function = Function(
                name="text_bm25",
                input_field_names=["text"],
                output_field_names=["sparse"],
                function_type=FunctionType.BM25
            )
            schema.add_function(bm25_function)
            
            collection = Collection(self.collection_name, schema)
            
            # Dense vector index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "AUTOINDEX",
                "params": {}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            
            # Sparse vector index
            sparse_index_params = {
                "metric_type": "BM25",
                "index_type": "SPARSE_INVERTED_INDEX",
                "params": {"drop_ratio_build": 0.2}
            }
            collection.create_index(field_name="sparse", index_params=sparse_index_params)
            
            collection.load()
            
    def upsert_image(self, image_id: str, title: str, category: str, tags: list[str], image_url: str, text: str, embedding: list[float]):
        if not self.connected and not self.connect():
            return
            
        try:
            collection = Collection(self.collection_name)
            data = [
                [image_id],
                [title],
                [category],
                [",".join(tags) if tags else ""],
                [image_url],
                [text],
                [embedding]
            ]
            collection.upsert(data)
            logger.info(f"Upserted image {image_id} to Zilliz.")
        except Exception as e:
            logger.error(f"Error upserting to Zilliz: {e}")

    def delete_image(self, image_id: str):
        if not self.connected and not self.connect():
            return
            
        try:
            collection = Collection(self.collection_name)
            expr = f'image_id == "{image_id}"'
            collection.delete(expr)
            logger.info(f"Deleted image {image_id} from Zilliz.")
        except Exception as e:
            logger.error(f"Error deleting from Zilliz: {e}")

    def get_image_embedding(self, image_id: str) -> list[float] | None:
        if not self.connected and not self.connect():
            return None
        try:
            collection = Collection(self.collection_name)
            results = collection.query(
                expr=f'image_id == "{image_id}"',
                output_fields=["embedding"],
                limit=1
            )
            if results:
                return results[0]["embedding"]
            return None
        except Exception as e:
            logger.error(f"Error querying Zilliz for embedding: {e}")
            return None

zilliz_service = ZillizService()
