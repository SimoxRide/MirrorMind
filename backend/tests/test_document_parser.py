from app.ingestion.document_parser import parse_document


def test_parse_text_document():
    parsed = parse_document("notes.txt", b"Hello\n\nWorld")

    assert parsed.document_type == "txt"
    assert parsed.text == "Hello\n\nWorld"
    assert parsed.was_truncated is False


def test_parse_json_document():
    parsed = parse_document("profile.json", b'{"name":"Ada","skills":["math"]}')

    assert parsed.document_type == "json"
    assert '"name": "Ada"' in parsed.text
    assert '"skills": [' in parsed.text


def test_parse_docx_document():
    import io
    from zipfile import ZipFile

    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:p><w:r><w:t>First paragraph.</w:t></w:r></w:p>
                <w:p><w:r><w:t>Second paragraph.</w:t></w:r></w:p>
              </w:body>
            </w:document>""",
        )

    parsed = parse_document("resume.docx", buffer.getvalue())

    assert parsed.document_type == "docx"
    assert parsed.text == "First paragraph.\n\nSecond paragraph."


def test_long_document_is_split_into_multiple_chunks():
    parsed = parse_document("memo.md", ("A" * 80).encode(), model_text_limit=40)

    assert parsed.was_truncated is False
    assert parsed.char_count == 80
    assert parsed.used_char_count == 80
    assert parsed.total_chunk_count == 2
    assert parsed.analyzed_chunk_count == 2
    assert [chunk.index for chunk in parsed.analysis_chunks] == [1, 2]


def test_document_analysis_chunk_limit_marks_partial_coverage():
    parsed = parse_document(
        "memo.md",
        ("A" * 120).encode(),
        model_text_limit=40,
        max_analysis_chunks=2,
    )

    assert parsed.was_truncated is True
    assert parsed.total_chunk_count == 3
    assert parsed.analyzed_chunk_count == 2
    assert [chunk.index for chunk in parsed.analysis_chunks] == [1, 3]
