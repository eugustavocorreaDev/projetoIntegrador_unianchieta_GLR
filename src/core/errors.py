"""Exceções de domínio, convertidas em respostas HTTP pela API."""


class RAGError(Exception):
    """Erro base do sistema."""


class ServiceUnavailableError(RAGError):
    """Um serviço externo (Ollama ou Qdrant) não respondeu."""


class EmbeddingError(ServiceUnavailableError):
    """Falha ao gerar embeddings."""


class LLMError(ServiceUnavailableError):
    """Falha ao gerar a resposta com o LLM."""


class CollectionNotFoundError(RAGError):
    """A coleção da estratégia pedida ainda não foi indexada."""


class RerankerError(RAGError):
    """O reranker não pôde ser carregado ou executado."""
