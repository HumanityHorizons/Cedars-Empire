"""Compact searchable, filterable, sortable, and exportable data tables for Cedars Empire."""
from __future__ import annotations

from html import escape
from io import BytesIO
import re


_TABLE_COUNTER = 0
_TABLE_SCOPE = "workspace"


def set_table_scope(scope: str) -> None:
    """Use separate widget state for each page."""
    global _TABLE_SCOPE
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(scope or "workspace").lower()).strip("_")
    _TABLE_SCOPE = cleaned or "workspace"


def reset_table_counter() -> None:
    """Reset stable table widget keys at the start of every Streamlit rerun."""
    global _TABLE_COUNTER
    _TABLE_COUNTER = 0


def _excel_bytes(frame: pd.DataFrame, include_index: bool) -> bytes:
    import pandas as pd
    buffer = BytesIO()
    export_frame = frame.copy()
    for column in export_frame.columns:
        if isinstance(export_frame[column].dtype, pd.DatetimeTZDtype):
            export_frame[column] = export_frame[column].dt.tz_convert(None)
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_frame.to_excel(writer, index=include_index, sheet_name="Records")
    return buffer.getvalue()


def _pdf_cell(value, style):
    import pandas as pd
    text = "" if value is None or (not isinstance(value, (list, dict, tuple)) and pd.isna(value)) else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Built-in PDF fonts are not universal Unicode fonts; replace unsupported glyphs safely.
    text = "".join(ch if ord(ch) <= 255 else "?" for ch in text)
    return __import__("reportlab.platypus", fromlist=["Paragraph"]).Paragraph(
        escape(text).replace("\n", "<br/>"), style
    )


def _pdf_bytes(frame: pd.DataFrame, table_number: int) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A3, A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import LongTable, SimpleDocTemplate, Spacer, Paragraph, TableStyle

    buffer = BytesIO()
    pagesize = landscape(A3 if len(frame.columns) > 8 else A4)
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesize, rightMargin=20, leftMargin=20,
        topMargin=24, bottomMargin=24, title=f"Cedars Empire data table {table_number:02d}"
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CedarsTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=13, leading=16, alignment=TA_LEFT, textColor=colors.HexColor("#0A2540"),
        spaceAfter=4
    )
    header_style = ParagraphStyle(
        "CedarsTableHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.5, leading=9, textColor=colors.white, spaceAfter=0
    )
    cell_style = ParagraphStyle(
        "CedarsTableCell", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7, leading=8.5, textColor=colors.HexColor("#0A2540"), spaceAfter=0,
        wordWrap="CJK"
    )
    values = [[_pdf_cell(col, header_style) for col in frame.columns]]
    for row in frame.itertuples(index=False, name=None):
        values.append([_pdf_cell(value, cell_style) for value in row])
    col_count = max(1, len(frame.columns))
    table = LongTable(
        values, repeatRows=1, colWidths=[doc.width / col_count] * col_count,
        hAlign="LEFT", splitByRow=1
    )
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2540")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F8FAFC")]),
    ]
    table.setStyle(TableStyle(style_commands))
    story = [
        Paragraph(f"Cedars Empire | Data Table {table_number:02d}", title_style),
        Spacer(1, 7),
        table
    ]
    doc.build(story)
    return buffer.getvalue()


def render_bank_table(data, use_container_width: bool = True, hide_index: bool = True, **kwargs) -> None:
    """Render a native sortable table with search, column filtering, and Excel/PDF export."""
    import pandas as pd
    import streamlit as st
    global _TABLE_COUNTER
    _TABLE_COUNTER += 1
    table_number = _TABLE_COUNTER
    key_root = f"ce_table_{_TABLE_SCOPE}_{table_number:02d}"

    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    elif isinstance(data, pd.Series):
        frame = data.to_frame()
    else:
        frame = pd.DataFrame(data)
    frame.columns = [str(column) for column in frame.columns]

    if frame.empty or len(frame.columns) == 0:
        st.dataframe(frame, use_container_width=use_container_width, hide_index=hide_index, **kwargs)
        return

    search_col, filter_col_col, filter_value_col = st.columns([2.2, 1.4, 1.8])
    with search_col:
        search_text = st.text_input("Search", placeholder="Search records", key=f"{key_root}_search")
    with filter_col_col:
        selected_column = st.selectbox(
            "Filter column", ["All columns"] + list(frame.columns), key=f"{key_root}_filter_column"
        )
    with filter_value_col:
        filter_value = st.text_input(
            "Filter value", placeholder="Contains…", key=f"{key_root}_filter_value",
            disabled=selected_column == "All columns"
        )

    filtered = frame
    if search_text.strip():
        search_mask = pd.Series(False, index=filtered.index)
        needle = search_text.strip()
        for column in filtered.columns:
            search_mask |= filtered[column].astype(str).str.contains(needle, case=False, regex=False, na=False)
        filtered = filtered.loc[search_mask]
    if selected_column != "All columns" and filter_value.strip():
        value_mask = filtered[selected_column].astype(str).str.contains(
            filter_value.strip(), case=False, regex=False, na=False
        )
        filtered = filtered.loc[value_mask]

    st.dataframe(
        filtered, use_container_width=use_container_width, hide_index=hide_index, **kwargs
    )
    left, right = st.columns([1, 1])
    try:
        excel_data = _excel_bytes(filtered, include_index=not hide_index)
        with left:
            st.download_button(
                "Excel", data=excel_data,
                file_name=f"cedars_empire_table_{table_number:02d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_root}_excel", use_container_width=True
            )
    except Exception:
        with left:
            st.button("Excel unavailable", key=f"{key_root}_excel_unavailable", disabled=True, use_container_width=True)

    try:
        pdf_data = _pdf_bytes(filtered, table_number)
        with right:
            st.download_button(
                "PDF", data=pdf_data,
                file_name=f"cedars_empire_table_{table_number:02d}.pdf",
                mime="application/pdf", key=f"{key_root}_pdf", use_container_width=True
            )
    except Exception:
        with right:
            st.button("PDF unavailable", key=f"{key_root}_pdf_unavailable", disabled=True, use_container_width=True)
