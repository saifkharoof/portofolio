from pymilvus import connections, MilvusClient
from langchain_milvus import Milvus, BM25BuiltInFunction
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
from loguru import logger


def _create_vector_store() -> Milvus | None:
    """
    Initialize a LangChain Milvus vector store with hybrid BM25 + dense search.

    Workaround for langchain-milvus 0.3.3 bug: the `col` property uses
    Collection(using=self.alias) where self.alias comes from MilvusClient._using
    (an auto-generated key). We pre-register this alias in the ORM connections
    registry so Collection() can resolve it.
    """
    if not (settings.zilliz_cloud_uri and settings.zilliz_cloud_token and settings.gemini_api_key):
        logger.warning("Vector DB or API Key configs missing. Vector store not initialized.")
        return None

    try:
        connection_args = {
            "uri": settings.zilliz_cloud_uri,
            "token": settings.zilliz_cloud_token,
        }

        # Step 1: Create MilvusClient to get its auto-generated alias
        probe_client = MilvusClient(**connection_args)
        auto_alias = probe_client._using  # e.g. "cm-128942306888976"

        # Step 2: Register an ORM connection under that exact alias so Collection()
        # can resolve it (fixes ConnectionNotExistException in langchain-milvus 0.3.3)
        connections.connect(alias=auto_alias, **connection_args)
        logger.debug(f"Registered ORM connection under alias '{auto_alias}'")

        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        )

        bm25_func = BM25BuiltInFunction(
            input_field_names="text",
            output_field_names="sparse",
        )

        vs = Milvus(
            embedding_function=embeddings,
            builtin_function=bm25_func,
            vector_field=["embedding", "sparse"],
            connection_args=connection_args,
            collection_name=settings.collection_name,
            auto_id=False,
        )

        logger.info("LangChain Milvus Hybrid Vector Store initialized successfully.")
        return vs

    except Exception as e:
        logger.error(f"Failed to initialize Milvus vector store: {e}")
        return None


class VectorDBService:
    def __init__(self):
        self.vector_store = _create_vector_store()

    def get_retriever(self, search_kwargs=None):
        if not self.vector_store:
            return None

        kwargs = search_kwargs or {"k": 5}
        return self.vector_store.as_retriever(search_kwargs=kwargs)


vector_db = VectorDBService()
