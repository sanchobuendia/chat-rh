from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader


class DocumentParser:
    SUPPORTED_EXTENSIONS = {".md", ".txt", ".csv", ".pdf", ".docx"}

    def parse(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in {".md", ".txt", ".csv"}:
            return file_path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        if suffix == ".docx":
            return self._parse_docx(file_path)
        raise ValueError(f"Unsupported file type for MVP: {suffix}")

    def list_supported_files(self, source_dir: Path) -> list[Path]:
        return sorted(
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    @staticmethod
    def _parse_pdf(file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(page for page in pages if page)

    @staticmethod
    def _parse_docx(file_path: Path) -> str:
        document = DocxDocument(str(file_path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)
