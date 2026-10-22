from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import pandas as pd
import pymupdf

import hh_table_ui as tables


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Investment": "Treasury", "Amount": "0.00", "Return": "—", "Status": "Verified"},
            {"Investment": "Grid", "Amount": "12.50", "Return": "—", "Status": "Pending"},
        ]
    )


def test_excel_export_is_a_valid_workbook_and_respects_hidden_index() -> None:
    frame = sample_frame()
    payload = tables._excel_bytes(frame, include_index=False)
    assert zipfile.is_zipfile(BytesIO(payload))
    parsed = pd.read_excel(BytesIO(payload))
    assert list(parsed.columns) == list(frame.columns)
    assert parsed["Investment"].tolist() == frame["Investment"].tolist()
    assert pd.to_numeric(parsed["Amount"]).tolist() == [0.0, 12.5]
    assert parsed["Return"].tolist() == frame["Return"].tolist()
    assert parsed["Status"].tolist() == frame["Status"].tolist()

    with_index = pd.read_excel(BytesIO(tables._excel_bytes(frame, include_index=True)))
    assert with_index.columns[0] == "Unnamed: 0"


def test_pdf_export_contains_table_headers_and_records() -> None:
    payload = tables._pdf_bytes(sample_frame(), table_number=1)
    assert payload.startswith(b"%PDF-")
    with pymupdf.open(stream=payload, filetype="pdf") as document:
        assert len(document) >= 1
        text = "\n".join(page.get_text() for page in document)
    assert "Investment" in text
    assert "Treasury" in text
    assert "Verified" in text


def test_shared_table_renderer_exposes_search_filter_native_sort_and_exports() -> None:
    source = Path("hh_table_ui.py").read_text(encoding="utf-8")
    assert 'st.text_input("Search"' in source
    assert '"Filter column"' in source
    assert 'st.text_input(' in source and 'placeholder="Contains…"' in source
    # Streamlit's native data grid provides clickable column-header sorting.
    assert "st.dataframe(" in source
    assert 'st.download_button(\n                "Excel"' in source
    assert 'st.download_button(\n                "PDF"' in source
