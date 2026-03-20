class ChunkerService:
    def split(self, text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
        text = " ".join(text.split())
        if len(text) <= chunk_size:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks
