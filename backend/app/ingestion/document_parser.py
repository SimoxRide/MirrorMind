"""Utilities for extracting text from supported document formats."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from pypdf import PdfReader

SUPPORTED_DOCUMENT_TYPES = {".pdf", ".docx", ".txt", ".md", ".json"}
DEFAULT_MODEL_TEXT_LIMIT = 12000
DEFAULT_MAX_ANALYSIS_CHUNKS = 6


class UnsupportedDocumentTypeError(ValueError):
    """Raised when a document type is not supported."""


@dataclass(slots=True)
class DocumentChunk:
    index: int
    total: int
    text: str


@dataclass(slots=True)
class ParsedDocument:
    filename: str
    document_type: str
    text: str
    char_count: int
    used_char_count: int
    was_truncated: bool
    total_chunk_count: int
    analyzed_chunk_count: int
    analysis_chunks: list[DocumentChunk]


def parse_document(
    filename: str,
    content: bytes,
    *,
    model_text_limit: int = DEFAULT_MODEL_TEXT_LIMIT,
    max_analysis_chunks: int = DEFAULT_MAX_ANALYSIS_CHUNKS,
) -> ParsedDocument:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_TYPES:
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type: {extension or 'unknown'}"
        )

    text = _extract_text(extension, content)
    normalized = _normalize_text(text)
    chunks, total_chunk_count, was_truncated = split_text_for_analysis(
        normalized,
        chunk_size=model_text_limit,
        max_chunks=max_analysis_chunks,
    )

    return ParsedDocument(
        filename=filename,
        document_type=extension.lstrip("."),
        text=normalized,
        char_count=len(normalized),
        used_char_count=sum(len(chunk.text) for chunk in chunks),
        was_truncated=was_truncated,
        total_chunk_count=total_chunk_count,
        analyzed_chunk_count=len(chunks),
        analysis_chunks=chunks,
    )


def _extract_text(extension: str, content: bytes) -> str:
    if extension == ".pdf":
        return _extract_pdf_text(content)
    if extension == ".docx":
        return _extract_docx_text(content)
    if extension in {".txt", ".md"}:
        return content.decode("utf-8", errors="replace")
    if extension == ".json":
        return _extract_json_text(content)
    raise UnsupportedDocumentTypeError(f"Unsupported document type: {extension}")


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx_text(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []

    for paragraph in root.findall(".//w:p", namespace):
        runs = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        if runs:
            paragraphs.append("".join(runs))

    return "\n\n".join(paragraphs)


def _extract_json_text(content: bytes) -> str:
    decoded = content.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        return decoded
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text_for_analysis(
    text: str,
    *,
    chunk_size: int = DEFAULT_MODEL_TEXT_LIMIT,
    max_chunks: int = DEFAULT_MAX_ANALYSIS_CHUNKS,
) -> tuple[list[DocumentChunk], int, bool]:
    """Split text into paragraph-aware chunks for model analysis."""
    if not text:
        return [], 0, False

    raw_chunks = _chunk_blocks(text, limit=chunk_size)
    total_chunk_count = len(raw_chunks)
    selected_chunks = _select_chunks(raw_chunks, max_chunks=max_chunks)
    wrapped_chunks = [
        DocumentChunk(index=index, total=total_chunk_count, text=chunk)
        for index, chunk in selected_chunks
    ]
    return wrapped_chunks, total_chunk_count, total_chunk_count > len(wrapped_chunks)


def _chunk_blocks(text: str, *, limit: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        parts = _split_large_block(paragraph, limit=limit)
        for part in parts:
            separator = 2 if current else 0
            projected = current_length + separator + len(part)
            if current and projected > limit:
                chunks.append("\n\n".join(current))
                current = [part]
                current_length = len(part)
            else:
                current.append(part)
                current_length = projected

    if current:
        chunks.append("\n\n".join(current))

    return chunks or [text[:limit]]


def _split_large_block(block: str, *, limit: int) -> list[str]:
    if len(block) <= limit:
        return [block]

    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if len(lines) > 1:
        parts: list[str] = []
        current = ""
        for line in lines:
            projected = f"{current}\n{line}".strip()
            if current and len(projected) > limit:
                parts.extend(_split_large_block(current, limit=limit))
                current = line
            else:
                current = projected
        if current:
            parts.extend(_split_large_block(current, limit=limit))
        return parts

    sentences = re.split(r"(?<=[.!?])\s+", block)
    if len(sentences) > 1:
        parts = []
        current = ""
        for sentence in sentences:
            projected = f"{current} {sentence}".strip()
            if current and len(projected) > limit:
                parts.append(current)
                current = sentence
            else:
                current = projected
        if current:
            parts.append(current)
        if all(len(part) <= limit for part in parts):
            return parts

    return [block[i : i + limit] for i in range(0, len(block), limit)]


def _select_chunks(chunks: list[str], *, max_chunks: int) -> list[tuple[int, str]]:
    indexed = list(enumerate(chunks, start=1))
    if len(indexed) <= max_chunks:
        return indexed
    if max_chunks <= 1:
        return [indexed[0]]
    return indexed[: max_chunks - 1] + [indexed[-1]]
