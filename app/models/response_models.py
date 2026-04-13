from pydantic import BaseModel
 
 
class ChunkResult(BaseModel):
    content: str
    source: str
    score: float

class MessageResponse(BaseModel):
    status: str
    text: str
    embedding_dimensions: int
    embedding_preview: list[float]
    chunks: list[ChunkResult]
