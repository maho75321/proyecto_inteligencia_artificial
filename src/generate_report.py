#!/usr/bin/env python3
"""Genera el informe APA 7 de la segunda unidad con índices funcionales.

El contenido técnico se conserva. El DOCX se construye con python-docx, se
actualizan el índice general, el de figuras y el de tablas con LibreOffice/UNO,
y se exporta un PDF temporal de verificación. No entrena modelos, no modifica
el dataset y no vuelve a ejecutar el EDA.

Requiere el Python del sistema con python-docx y LibreOffice/UNO disponibles;
el entorno .venv del análisis no incluye UNO.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import uno
from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
REPORT = ROOT / "report"
DOCX = REPORT / "informe_segunda_unidad.docx"
PDF = Path(tempfile.gettempdir()) / "informe_segunda_unidad.pdf"

FONT = "Times New Roman"
TEXT_WIDTH_CM = 21.0 - 2.54 * 2
ALIGN_LEFT = "left"
TABLE_NUMBER = 0
FIGURE_NUMBER = 0


def _font(style_or_run, size=None, bold=None, italic=None, color=None):
    font = style_or_run.font
    font.name = FONT
    if size is not None:
        font.size = Pt(size)
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic
    if color is not None:
        font.color.rgb = RGBColor.from_string(color)
    rpr = getattr(style_or_run, "_element", None)
    if rpr is not None:
        rpr = rpr.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rfonts.set(qn(attr), FONT)


def _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, line=2.0,
                      before=0, after=0, first_indent=0.0, left_indent=0.0,
                      keep_next=False, keep_together=False):
    pf = p.paragraph_format
    pf.alignment = alignment
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.first_line_indent = Cm(first_indent)
    pf.left_indent = Cm(left_indent)
    pf.keep_with_next = keep_next
    pf.keep_together = keep_together
    pf.widow_control = True


def _add_style(doc, name, base="Normal", size=12, bold=False, italic=False,
               alignment=WD_ALIGN_PARAGRAPH.LEFT, line=2.0, before=0,
               after=0, first_indent=0.0, left_indent=0.0, keep_next=False,
               keep_together=False, page_break=False):
    styles = doc.styles
    if name in styles:
        st = styles[name]
    else:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = styles[base]
    _font(st, size=size, bold=bold, italic=italic, color="000000")
    pf = st.paragraph_format
    pf.alignment = alignment
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.first_line_indent = Cm(first_indent)
    pf.left_indent = Cm(left_indent)
    pf.keep_with_next = keep_next
    pf.keep_together = keep_together
    pf.page_break_before = page_break
    pf.widow_control = True
    return st


def setup_document(doc):
    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(2.54)
    sec.right_margin = Cm(2.54)
    sec.header_distance = Cm(1.27)
    sec.footer_distance = Cm(1.27)

    # Normal: cuerpo APA 7
    normal = doc.styles["Normal"]
    _font(normal, size=12, color="000000")
    _add_style(doc, "Text body", size=12, line=2.0, first_indent=1.27)
    _add_style(doc, "Title", size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    _add_style(doc, "Subtitle", size=12, italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    _add_style(doc, "Heading 1", size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER,
               line=2.0, keep_next=True, keep_together=True)
    _add_style(doc, "Heading 2", size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
               line=2.0, keep_next=True, keep_together=True)
    _add_style(doc, "Heading 3", size=12, bold=True, italic=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
               line=2.0, keep_next=True, keep_together=True)
    _add_style(doc, "Heading 4", size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
               line=2.0, first_indent=1.27, keep_next=True, keep_together=True)
    _add_style(doc, "Heading 5", size=12, bold=True, italic=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
               line=2.0, first_indent=1.27, keep_next=True, keep_together=True)
    _add_style(doc, "Bullet", size=12, line=2.0, left_indent=0.63, first_indent=-0.63)
    _add_style(doc, "Numbered", size=12, line=2.0, left_indent=0.95, first_indent=-0.63)
    _add_style(doc, "Reference", size=12, line=2.0, left_indent=1.27, first_indent=-1.27)
    _add_style(doc, "Table Caption", size=12, line=1.0, before=6, after=3, keep_next=True)
    _add_style(doc, "Figure Caption", size=12, line=1.0, before=6, after=3, keep_next=True)
    _add_style(doc, "Table Text", size=9, line=1.0)
    _add_style(doc, "Table Note", size=10, line=1.0, before=3, after=6)
    _add_style(doc, "Figure Image", size=12, alignment=WD_ALIGN_PARAGRAPH.CENTER,
               line=1.0, before=3, after=0, keep_next=True, keep_together=True)
    _add_style(doc, "Figure Note", size=10, line=1.0, before=3, after=6)
    _add_style(doc, "Cover Title", size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    _add_style(doc, "Cover Subtitle", size=12, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    _add_style(doc, "Cover Meta", size=12, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    _add_style(doc, "Index Heading", size=12, bold=True,
               alignment=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, before=0, after=12,
               keep_next=True)
    _add_style(doc, "Index Field", size=12, line=1.0)

    for level in range(1, 4):
        st = _add_style(doc, f"TOC {level}", size=12, line=1.0, before=0, after=2,
                        left_indent=0.0 if level == 1 else 0.5 * (level - 1))
        st.paragraph_format.first_line_indent = Cm(0)
    # Estilo que LibreOffice usa para las listas de ilustraciones.
    if "Table of Figures" in doc.styles:
        st = doc.styles["Table of Figures"]
        _font(st, size=12, color="000000")
        st.paragraph_format.line_spacing = 1.0
        st.paragraph_format.space_after = Pt(2)
        st.paragraph_format.left_indent = Cm(0)
        st.paragraph_format.first_line_indent = Cm(0)

    # Encabezado APA: solo número de página, esquina superior derecha.
    header = sec.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.space_after = Pt(0)
    hp.paragraph_format.line_spacing = 1.0
    _add_page_field(hp)
    for p in sec.footer.paragraphs:
        p.text = ""

    # Evita que Word pregunte por la actualización de campos.
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)


def _add_page_field(paragraph):
    run = paragraph.add_run()
    _font(run, size=12)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    run._r.append(begin)
    run = paragraph.add_run()
    _font(run, size=12)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    run._r.append(instr)
    run = paragraph.add_run()
    _font(run, size=12)
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run._r.append(sep)
    result = paragraph.add_run("1")
    _font(result, size=12)
    end_run = paragraph.add_run()
    _font(end_run, size=12)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)


def _add_field(paragraph, instruction, result="", bold=False, italic=False):
    run = paragraph.add_run()
    _font(run, bold=bold, italic=italic)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    run._r.append(begin)
    run = paragraph.add_run()
    _font(run, bold=bold, italic=italic)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run._r.append(instr)
    run = paragraph.add_run()
    _font(run, bold=bold, italic=italic)
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run._r.append(sep)
    if result:
        rr = paragraph.add_run(result)
        _font(rr, bold=bold, italic=italic)
    run = paragraph.add_run()
    _font(run, bold=bold, italic=italic)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(end)


def add_seq_field(paragraph, label, number):
    _add_field(paragraph, f"SEQ {label} \\* ARABIC", str(number), bold=True)


def add_cover(doc):
    add_blank(doc, 3)
    p = doc.add_paragraph("Análisis comparativo de algoritmos de aprendizaje automático para la detección de sitios web de phishing mediante características de las URL", style="Cover Title")
    _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    p = doc.add_paragraph("Análisis exploratorio, preprocesamiento, partición y diseño preliminar de modelos", style="Cover Subtitle")
    _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)
    add_blank(doc, 1)
    for text in [
        "[Nombre completo del estudiante]",
        "Ingeniería de Sistemas, Universidad Andina del Cusco",
        "Inteligencia Artificial — Segunda unidad",
        "Docente: [Nombre del docente]",
        "25 de octubre de 2026",
    ]:
        p = doc.add_paragraph(text, style="Cover Meta")
        _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=2.0)


def add_indices(doc):
    pages = [
        ("Índice general", ' TOC \\o "1-3" \\h \\z \\u '),
        ("Índice de figuras", ' TOC \\h \\z \\c "Figura" '),
        ("Índice de tablas", ' TOC \\h \\z \\c "Tabla" '),
    ]
    for title, instruction in pages:
        p = doc.add_paragraph(title, style="Index Heading")
        p.paragraph_format.page_break_before = True
        p = doc.add_paragraph(style="Index Field")
        p.paragraph_format.page_break_before = False
        _add_field(p, instruction, "Actualice el campo para generar este índice.")


def add_blank(doc, count=1):
    for _ in range(count):
        p = doc.add_paragraph("", style="Text body")
        _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, line=2.0, first_indent=0)


def new_cursor(doc):
    return None


def add_markup(doc, text, style="Text body", page_break=False, align=None,
               keep_with_next=None, space_after=None):
    p = doc.add_paragraph(style=style)
    if style == "Heading 1":
        page_break = True
    p.paragraph_format.page_break_before = page_break
    if align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if keep_with_next is not None:
        p.paragraph_format.keep_with_next = keep_with_next
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after / 40.0)
    bold = False
    italic = False
    for token in re.split(r"(\*\*|\*)", text.replace("`", "")):
        if token == "**":
            bold = not bold
        elif token == "*":
            italic = not italic
        elif token:
            r = p.add_run(token)
            _font(r, bold=True if bold else None, italic=True if italic else None)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="Bullet")
        r = p.add_run("•  " + item.replace("`", ""))
        _font(r)
        _paragraph_format(p, line=2.0, left_indent=0.63, first_indent=-0.63)


def add_numbered(doc, items):
    for index, item in enumerate(items, start=1):
        p = doc.add_paragraph(style="Numbered")
        r = p.add_run(f"{index}.  " + item.replace("`", ""))
        _font(r)
        _paragraph_format(p, line=2.0, left_indent=0.95, first_indent=-0.63)


def _split_caption(caption, label, number):
    prefix = re.compile(rf"^{label}\s+{number}\.\s*", re.IGNORECASE)
    text = prefix.sub("", caption).replace("`", "").strip()
    source = ""
    if "Fuente:" in text:
        text, source = text.split("Fuente:", 1)
        text = text.strip()
        source = "Fuente: " + source.strip()
    text = text.strip()
    parts = re.split(r"(?<=\.)\s+", text, maxsplit=1)
    title = parts[0].rstrip(".").strip()
    extra = parts[1].strip() if len(parts) > 1 else ""
    note = " ".join(x for x in [extra, source] if x).strip()
    return title, note


def _bookmark(paragraph, name, bookmark_id):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    pPr = paragraph._p.pPr
    if pPr is not None:
        pPr.addnext(start)
    else:
        paragraph._p.insert(0, start)
    paragraph._p.append(end)


def _caption(doc, text, label, number, style, page_break=False):
    p = doc.add_paragraph(style=style)
    if page_break:
        p.paragraph_format.page_break_before = True
    r = p.add_run(f"{label} ")
    _font(r, bold=True)
    add_seq_field(p, label, number)
    r = p.add_run(". ")
    _font(r, bold=True)
    r = p.add_run(text)
    _font(r, italic=True)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.keep_together = True
    base_id = 1000 if label == "Tabla" else 2000
    _bookmark(p, f"{label.lower()}_{number}", base_id + number)
    return p


def _note(doc, note, style):
    if not note:
        return
    p = doc.add_paragraph(style=style)
    r = p.add_run("Nota. ")
    _font(r, size=10, italic=True)
    r = p.add_run(note)
    _font(r, size=10)
    p.paragraph_format.first_line_indent = Cm(0)


def add_figure(doc, filename, caption, width_cm):
    global FIGURE_NUMBER
    FIGURE_NUMBER += 1
    number = FIGURE_NUMBER
    title, note = _split_caption(caption, "Figura", number)
    path = FIGURES / filename
    if not path.exists():
        raise FileNotFoundError(path)
    _caption(doc, title, "Figura", number, "Figure Caption")
    with Image.open(path) as image:
        pixel_width, pixel_height = image.size
    width = min(width_cm, TEXT_WIDTH_CM - 0.2)
    p = doc.add_paragraph(style="Figure Image")
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width))
    _paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, line=1.0,
                      before=3, after=0, keep_next=True, keep_together=True)
    _note(doc, note, "Figure Note")


def _set_cell_margins(cell, left=60, right=60, top=30, bottom=30):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.find(qn("w:tcMar"))
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for tag, value in (("w:top", top), ("w:left", left), ("w:bottom", bottom), ("w:right", right)):
        el = tcMar.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            tcMar.append(el)
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")


def _set_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        if edge in ("top", "bottom"):
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "6")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")
        else:
            el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def _set_cell_bottom_border(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), "000000")
    tcBorders.append(bottom)


def add_table(doc, caption, headers, rows, widths, font_size=8.5, page_break=False):
    global TABLE_NUMBER
    TABLE_NUMBER += 1
    number = TABLE_NUMBER
    title, note = _split_caption(caption, "Tabla", number)
    _caption(doc, title, "Tabla", number, "Table Caption", page_break=page_break)
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    table.allow_autofit = False
    _set_table_borders(table)
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    total_cm = TEXT_WIDTH_CM
    for idx, width in enumerate(widths):
        cm = total_cm * width / sum(widths)
        table.columns[idx].width = Cm(cm)
        for cell in table.columns[idx].cells:
            cell.width = Cm(cm)

    font_size = float(font_size)
    for col, header in enumerate(headers):
        cell = table.cell(0, col)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        _set_cell_margins(cell)
        _set_cell_bottom_border(cell)
        p = cell.paragraphs[0]
        p.style = doc.styles["Table Text"]
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(str(header).replace("`", ""))
        _font(r, size=font_size, bold=True)

    for row_index, row in enumerate(rows, start=1):
        for col, value in enumerate(row):
            cell = table.cell(row_index, col)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            _set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.style = doc.styles["Table Text"]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(str(value).replace("`", ""))
            _font(r, size=font_size)

    trPr = table.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    trPr.append(tblHeader)
    for row_index, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        cantSplit = OxmlElement("w:cantSplit")
        trPr.append(cantSplit)
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True
    _note(doc, note, "Table Note")


def add_references(doc):
    add_markup(doc, "Referencias", "Heading 1", page_break=True)
    references = [
        "Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32. https://doi.org/10.1023/A:1010933404324",
        "Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. En *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785–794). Association for Computing Machinery. https://doi.org/10.1145/2939672.2939785",
        "Dam Minh, L., & Tran Cong, H. (2026). *URL-Phish: A feature-engineered dataset for phishing detection* (Version 2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/65z9twcx3r.2",
        "Fawcett, T. (2006). An introduction to ROC analysis. *Pattern Recognition Letters, 27*(8), 861–874. https://doi.org/10.1016/j.patrec.2005.10.010",
        "Hastie, T., Tibshirani, R., & Friedman, J. (2009). *The elements of statistical learning: Data mining, inference, and prediction* (2.ª ed.). Springer. https://doi.org/10.1007/978-0-387-84858-7",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830. https://jmlr.org/papers/v12/pedregosa11a.html",
        "Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLOS ONE, 10*(3), e0118432. https://doi.org/10.1371/journal.pone.0118432",
    ]
    for reference in references:
        p = doc.add_paragraph(style="Reference")
        parts = reference.split("*")
        for index, part in enumerate(parts):
            if not part:
                continue
            r = p.add_run(part)
            _font(r, italic=(index % 2 == 1))


def build_body(doc):
    # 1. Título del proyecto
    add_markup(doc, "1. Título del proyecto", "Heading 1", page_break=True)
    add_markup(
        doc,
        "**Análisis comparativo de algoritmos de aprendizaje automático para la detección de sitios web de phishing mediante características de las URL**",
        "Title",
    )
    add_markup(
        doc,
        "El título delimita el objeto de la investigación formativa: comparar enfoques de aprendizaje automático aplicables a datos tabulares para clasificar una URL como benigna o de phishing, utilizando características extraídas de la propia URL. La palabra “comparativo” describe el diseño metodológico previsto; no implica que en este avance existan resultados experimentales de comparación.",
    )
    add_markup(
        doc,
        "Este documento corresponde al avance de la segunda unidad. Integra el EDA, el preprocesamiento, la partición y el diseño preliminar de modelos. El entrenamiento y la evaluación quedan fuera de su alcance y requerirán una autorización posterior.",
    )

    # 2. Planteamiento del problema y objetivos
    add_markup(doc, "2. Planteamiento del problema y objetivos", "Heading 1", page_break=True)
    add_markup(doc, "2.1 Contexto y problema", "Heading 2")
    add_markup(
        doc,
        "El phishing es una forma de fraude en la que un atacante suplanta la identidad de una organización o servicio para obtener credenciales, datos personales o información financiera. La URL es una de las primeras señales observables antes de interactuar con una página y puede analizarse con características léxicas y estructurales de bajo costo. El conjunto URL-Phish v2 reúne 116 600 URL etiquetadas y 22 características numéricas (Dam Minh & Tran Cong, 2026); en este proyecto se emplea como fuente principal.",
    )
    add_markup(
        doc,
        "El problema no se reduce a elegir un algoritmo. El dataset presenta desbalance de clases, duplicados exactos, dominios con etiquetas contradictorias, variables redundantes y una posible diferencia de recolección asociada a HTTPS. Si se divide aleatoriamente por filas, un mismo dominio puede quedar en entrenamiento y prueba, y el modelo podría aprender patrones del dominio en lugar de generalizar a dominios no vistos. Esa fuga produciría una estimación artificialmente optimista. Por ello, el problema metodológico central es diseñar una comparación reproducible que controle la fuga por dominio, trate el desbalance y reserve la prueba para una evaluación final.",
    )
    add_markup(doc, "2.2 Pregunta de investigación", "Heading 2")
    add_markup(
        doc,
        "¿Cómo diseñar una comparación metodológicamente válida de modelos de aprendizaje automático para clasificar URL benignas y de phishing, evitando la fuga de información por dominio y usando métricas adecuadas al desbalance?",
    )
    add_markup(doc, "2.3 Objetivo general", "Heading 2")
    add_markup(
        doc,
        "Analizar comparativamente algoritmos de aprendizaje automático aplicables a datos tabulares para la detección de phishing a partir de características de URL, mediante un diseño reproducible de análisis exploratorio, preprocesamiento, partición y selección preliminar de modelos.",
    )
    add_markup(doc, "2.4 Objetivos específicos", "Heading 2")
    add_numbered(
        doc,
        [
            "Describir la estructura y la calidad del dataset, incluyendo clases, faltantes, duplicados, dominios contradictorios y relaciones entre variables.",
            "Definir un conjunto de predictores y un preprocesamiento que evite el uso de identificadores y que ajuste cualquier transformación solo con entrenamiento.",
            "Construir y justificar una partición agrupada por dominio que no comparta filas, URL ni dominios entre entrenamiento, validación y prueba.",
            "Diseñar modelos candidatos, configuraciones iniciales, métricas y un protocolo de selección que reserve la prueba para una evaluación final única.",
            "Documentar limitaciones, riesgos residuales y decisiones pendientes antes de cualquier entrenamiento.",
        ],
    )
    add_markup(doc, "2.5 Justificación y alcance", "Heading 2")
    add_markup(
        doc,
        "La utilidad del trabajo es metodológica y formativa. Un diseño explícito permite que los resultados posteriores sean comparables, reproducibles y defendibles, y evita confundir una propuesta con un hallazgo. Las características de URL son económicas de calcular y pueden apoyar filtros previos, pero no sustituyen un análisis del contenido, del certificado o del contexto de navegación. Esta limitación se declara desde el planteamiento.",
    )
    add_markup(
        doc,
        "El alcance de este informe comprende las cinco secciones solicitadas por el docente: título, planteamiento y objetivos, EDA, preprocesamiento y partición, y diseño preliminar de modelos. **No se entrenaron modelos, no se calcularon métricas de rendimiento y no se declara superioridad de un algoritmo.**",
    )

    # 3. EDA
    add_markup(doc, "3. Análisis exploratorio de datos (EDA)", "Heading 1", page_break=True)
    add_markup(doc, "3.1 Método y alcance del EDA", "Heading 2")
    add_markup(
        doc,
        "El EDA se ejecutó en la Fase 2 con Python 3.12.3, pandas 3.1.0, NumPy 2.5.4, Matplotlib 3.11.2, Seaborn 0.13.2 y SciPy 1.18.1. Produjo 18 tablas y 6 figuras. Para este informe se revisaron los archivos ya generados; no se volvió a ejecutar el análisis completo. El EDA es descriptivo: mide y documenta, pero no entrena modelos ni demuestra causalidad.",
    )
    add_markup(doc, "3.2 Dimensiones y distribución de clases", "Heading 2")
    add_markup(
        doc,
        "El archivo contiene 116 600 registros y 26 columnas: 23 columnas numéricas (22 características y la etiqueta `label`) y 3 columnas de texto (`url`, `dom` y `tld`). La variable objetivo tiene dos valores: 0 para benigno y 1 para phishing. La distribución se muestra en la Tabla 1 y en la Figura 1.",
    )
    add_table(
        doc,
        "Tabla 1. Distribución de la variable objetivo en el dataset original. Fuente: elaboración propia a partir de `results/tables/03_distribucion_label.csv`.",
        ["Clase", "Registros", "Porcentaje"],
        [
            ["0 — benigno", "100 000", "85,7633 %"],
            ["1 — phishing", "16 600", "14,2367 %"],
            ["Total", "116 600", "100,0000 %"],
        ],
        [28, 26, 26],
    )
    add_figure(
        doc,
        "fig01_distribucion_clases.png",
        "Figura 1. Distribución de clases del dataset original. La clase benigna concentra la mayor parte de los registros. Fuente: elaboración propia.",
        12.5,
    )
    add_markup(
        doc,
        "La proporción es aproximadamente 6,02 casos benignos por cada caso de phishing. Esta observación tiene una consecuencia directa: la exactitud (*accuracy*) no es una métrica suficiente, porque un clasificador que siempre prediga “benigno” obtendría cerca del 85,76 % de aciertos y, al mismo tiempo, detectaría cero casos de phishing. Por eso el diseño posterior prioriza el recall de la clase 1 y la curva precision-recall (Saito & Rehmsmeier, 2015).",
    )
    add_markup(doc, "3.3 Calidad de los datos", "Heading 2")
    add_markup(
        doc,
        "Solo `tld` presenta valores faltantes: 14 casos, equivalentes al 0,0120 % del total. Trece corresponden a direcciones IP y uno a una URL malformada; en los 14 casos `tld_len` es cero. El faltante es estructural, por lo que no debe imputarse un TLD inventado. La Figura 2 muestra que el resto de las columnas no tiene faltantes.",
    )
    add_figure(
        doc,
        "fig02_valores_faltantes.png",
        "Figura 2. Valores faltantes por columna. Solo `tld` presenta 14 faltantes. Fuente: elaboración propia.",
        12.5,
    )
    add_table(
        doc,
        "Tabla 2. Principales hallazgos de calidad del dataset original. Fuente: elaboración propia a partir de `results/tables/05_valores_faltantes.csv`, `06_duplicados_resumen.csv`, `08_resumen_dominios.csv` y `11_constantes_casi_constantes.csv`.",
        ["Aspecto", "Hallazgo", "Consecuencia metodológica"],
        [
            ["Faltantes", "14 en `tld` (0,0120 %): 13 IP y 1 URL malformada.", "No imputar; `tld` queda fuera del conjunto primario."],
            ["Filas duplicadas", "1 369 filas sobrantes en 1 007 grupos (1,1741 %).", "Eliminar duplicados exactos antes de modelar."],
            ["URL repetidas", "Los mismos 1 007 grupos; no hay etiquetas contradictorias para una misma URL.", "La URL no se usa como predictor."],
            ["Dominios repetidos", "5 258 grupos y 25 740 filas sobrantes (22,0755 %).", "No son filas duplicadas; se agrupa por dominio."],
            ["Dominios contradictorios", "24 dominios y 4 402 filas (3,7753 %).", "Conservar y documentar; no reetiquetar sin evidencia."],
            ["Variable casi constante", "`is_ip`: 13 valores 1 (0,0111 %).", "Excluir del conjunto primario; evaluar como sensibilidad."],
        ],
        [20, 37, 43],
        font_size=8.0,
    )
    add_markup(
        doc,
        "Los 1 369 duplicados exactos son filas idénticas en las 26 columnas. No se detectó una misma URL con características distintas ni una misma URL con etiquetas distintas. En cambio, los dominios repetidos no equivalen a filas duplicadas: un dominio puede agrupar muchas URL diferentes. Además, 226 filas y 32 valores de `dom` conservaban el prefijo `www.`; al normalizarlo, los dominios únicos pasaron de 90 860 a 90 859 y los dominios contradictorios siguieron siendo 24. La Fase 3 aplicó además minúsculas y eliminación del punto final, con lo que obtuvo 90 858 dominios normalizados.",
    )
    add_markup(doc, "3.4 Distribuciones y diferencias entre clases", "Heading 2")
    add_markup(
        doc,
        "La Figura 3 presenta las distribuciones de las variables numéricas relevantes y la Figura 4 compara algunas de ellas por clase. Dieciocho de las 22 variables numéricas presentan asimetría absoluta mayor que 1. Los máximos observados incluyen `url_len = 1 202`, `path_len = 670`, `query_len = 1 148`, `letter_cnt = 1 037`, `digit_cnt = 321`, `special_cnt = 234` y `entropy = 6,03`.",
    )
    add_figure(
        doc,
        "fig03_distribuciones_numericas.png",
        "Figura 3. Distribuciones de variables numéricas relevantes, con escala logarítmica y mediana marcada. El recorte visual en el percentil 99,5 no elimina datos. Fuente: elaboración propia.",
        16.0,
    )
    add_figure(
        doc,
        "fig04_comparacion_clases.png",
        "Figura 4. Comparación de variables seleccionadas por clase, sin valores extremos gráficos y con eje recortado en el percentil 99,5. Fuente: elaboración propia.",
        16.0,
    )
    add_markup(
        doc,
        "Las diferencias descriptivas son claras. La clase 1 presenta mayor entropía media (4,316 frente a 3,789), mayor longitud media de URL (56,305 frente a 29,076), más dígitos (5,753 frente a 0,146) y mayor longitud de ruta (17,153 frente a 4,605). La clase 0 presenta mayor proporción media de caracteres especiales (0,243 frente a 0,184) y un dominio ligeramente más largo. HTTPS aparece en el 35,09 % de la clase 0 y en el 91,43 % de la clase 1.",
    )
    add_markup(
        doc,
        "Estas cifras son observaciones descriptivas, no relaciones causales. El criterio de 1,5 × IQR marca porcentajes altos en variables discretas con muchos ceros, como `subdom_cnt` (24,37 %) o `slash_cnt` (29,30 %); por ello no se eliminan valores extremos de forma automática. Los máximos pueden corresponder a URL reales y forman parte del fenómeno que se desea estudiar.",
    )
    add_markup(doc, "3.5 Correlaciones y redundancia", "Heading 2")
    add_markup(
        doc,
        "La Figura 5 presenta la matriz de correlación de Pearson. Dos pares superan |r| ≥ 0,90: `url_len`–`letter_cnt` (r = 0,972) y `eq_cnt`–`amp_cnt` (r = 0,928). También aparecen asociaciones fuertes entre `path_len`–`special_cnt` (r = 0,782), `spec_ratio`–`entropy` (r = −0,726), `dot_cnt`–`subdom_cnt` (r = 0,681) y `slash_cnt`–`path_len` (r = 0,680).",
    )
    add_figure(
        doc,
        "fig05_matriz_correlacion.png",
        "Figura 5. Matriz de correlación de Pearson entre las variables numéricas. Los valores miden asociación lineal, no causalidad. Fuente: elaboración propia.",
        14.5,
    )
    add_markup(
        doc,
        "Las variables con mayor asociación lineal con `label` son `digit_ratio` (r = 0,518), `entropy` (r = 0,513), `is_https` (r = 0,398), `spec_ratio` (r = −0,385), `digit_cnt` (r = 0,329) y `url_len` (r = 0,324). La redundancia no implica eliminar variables de forma automática: en un modelo lineal puede volver inestables los coeficientes; en modelos de árboles puede repartir la importancia entre variables correlacionadas. Por eso el diseño inicial conserva los 21 predictores y trata la redundancia como una limitación interpretativa.",
    )
    add_markup(doc, "3.6 Dominios con etiquetas contradictorias", "Heading 2")
    add_markup(
        doc,
        "La Figura 6 y la Tabla 3 muestran los dominios que contienen ambas clases. En el dataset original son 24 dominios y 4 402 filas; después de eliminar duplicados exactos quedan 4 391 filas, el 3,81 % del conjunto de modelado. `weebly.com` y `google.com` son mayoritariamente clase 1, mientras que `wordpress.com` es mayoritariamente clase 0. Esto sugiere que la etiqueta no depende solo del dominio y que puede estar asociada a la URL o al contenido específico.",
    )
    add_figure(
        doc,
        "fig06_dominios_contradictorios.png",
        "Figura 6. Composición porcentual de los 24 dominios con etiquetas contradictorias. La barra está normalizada al 100 % dentro de cada dominio. Fuente: elaboración propia.",
        13.5,
    )
    add_table(
        doc,
        "Tabla 3. Principales dominios con etiquetas contradictorias después de la deduplicación. Fuente: elaboración propia a partir de `results/tables/24_dominios_contradictorios_particion.csv`.",
        ["Dominio", "Filas", "Clase 0", "Clase 1", "% clase 1", "Partición"],
        [
            ["weebly.com", "2 455", "11", "2 444", "99,55 %", "Prueba"],
            ["google.com", "1 450", "11", "1 439", "99,24 %", "Validación"],
            ["wixsite.com", "160", "10", "150", "93,75 %", "Entrenamiento"],
            ["dropbox.com", "109", "1", "108", "99,08 %", "Entrenamiento"],
            ["blogspot.com", "63", "4", "59", "93,65 %", "Entrenamiento"],
            ["wordpress.com", "39", "38", "1", "2,56 %", "Entrenamiento"],
        ],
        [22, 10, 11, 11, 14, 32],
    )
    add_markup(
        doc,
        "No se reetiquetaron ni se excluyeron estos dominios. La fuente combina dominios benignos con URL de phishing alojadas en servicios legítimos o compartidos; decidir cuál es el caso sin evidencia del contenido introduciría una decisión no respaldada. La partición agrupada asigna cada dominio completo a una sola partición, de modo que la contradicción no se convierte en fuga entre entrenamiento y prueba.",
    )
    add_markup(doc, "3.7 Síntesis del EDA", "Heading 2", page_break=True)
    add_markup(doc, "**Observaciones:**", "Text body", keep_with_next=True)
    add_bullets(
        doc,
        [
            "El dataset está desbalanceado: 85,7633 % benigno y 14,2367 % phishing.",
            "Existen 1 369 duplicados exactos y 24 dominios con etiquetas contradictorias.",
            "La repetición de dominios es alta, pero no equivale a duplicación de filas.",
            "Varias variables tienen colas largas y existen pares con correlación superior a 0,90.",
            "HTTPS se distribuye de forma muy distinta entre clases: 35,09 % frente a 91,43 %.",
        ],
    )
    add_markup(doc, "**Interpretaciones y decisiones derivadas:**", "Text body", keep_with_next=True)
    add_bullets(
        doc,
        [
            "La exactitud no debe ser el criterio principal; se necesitan recall, precision, F1, PR-AUC, ROC-AUC y matriz de confusión.",
            "Los duplicados deben eliminarse y la partición debe agruparse por dominio para evitar una evaluación optimista.",
            "Los dominios contradictorios se conservan y se documentan; no se reetiquetan sin evidencia.",
            "La redundancia y el posible artefacto de `is_https` se tratarán como análisis de sensibilidad, no como eliminación automática.",
            "El EDA no demuestra que un modelo funcionará; solo informa decisiones de preprocesamiento y evaluación.",
        ],
    )

    # 4. Preprocesamiento
    add_markup(doc, "4. Preprocesamiento y partición de datos", "Heading 1", page_break=True)
    add_markup(doc, "4.1 Integridad del archivo y limpieza", "Heading 2")
    add_markup(
        doc,
        "El archivo `Dataset.csv` conserva el siguiente SHA-256 antes y después de la Fase 3:",
    )
    add_markup(
        doc,
        "d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1",
        align=ALIGN_LEFT,
        space_after=240,
    )
    add_markup(
        doc,
        "No se modificó el CSV original. La limpieza eliminó 1 369 filas duplicadas exactas, conservando la primera aparición. La Tabla 4 resume el efecto sobre el número de filas y las clases.",
    )
    add_table(
        doc,
        "Tabla 4. Efecto de la deduplicación sobre el conjunto de datos. Fuente: elaboración propia a partir de `results/tables/29_resumen_fase3.json`.",
        ["Concepto", "Filas", "Clase 0", "Clase 1", "Observación"],
        [
            ["Dataset original", "116 600", "100 000", "16 600", "Archivo sin modificar."],
            ["Duplicados eliminados", "1 369", "1 359", "10", "Se conservó la primera aparición."],
            ["Conjunto de modelado", "115 231", "98 641", "16 590", "URL únicas y sin duplicados exactos."],
        ],
        [22, 11, 12, 12, 43],
    )
    add_markup(
        doc,
        "La eliminación de duplicados es necesaria porque una fila repetida no aporta información nueva y, si se distribuye entre entrenamiento y prueba, produce una evaluación optimista. La operación reduce el conjunto en 1,1741 % y no altera la semántica de las etiquetas.",
    )
    add_markup(doc, "4.2 Procedencia y semántica de las etiquetas", "Heading 2")
    add_markup(
        doc,
        "La fuente identificada es **URL-Phish: A Feature-Engineered Dataset for Phishing Detection**, versión 2, DOI `10.17632/65z9twcx3r.2`, publicada el 9 de marzo de 2026 por Dam Minh y Tran Cong (2026). La ficha de la fuente indica 116 600 URL, 100 000 muestras benignas (`label = 0`) y 16 600 muestras de phishing (`label = 1`), con 22 características numéricas y tres columnas de referencia (`url`, `dom`, `tld`). La descripción de DataCite señala que los casos benignos provienen de Research Organization Registry y los de phishing de PhishTank, recolectados entre noviembre de 2024 y septiembre de 2025.",
    )
    add_markup(
        doc,
        "La identificación se sustenta en la coincidencia de filas, clases, columnas, nombres de variables y fecha, y en la coincidencia del tamaño (15 149 338 bytes) y del SHA-256 local con los metadatos públicos del archivo publicado en Mendeley v2. No se realizó una descarga directa adicional. La ficha de DataCite describe las URL como únicas y afirma que una limpieza eliminó duplicados; sin embargo, el archivo publicado contiene 1 369 duplicados exactos. La discrepancia se documenta y se resolvió con la deduplicación; no se atribuye a una modificación local. **La semántica `0 = benigno` y `1 = phishing` está confirmada por la fuente, no es una hipótesis inferida.**",
    )
    add_markup(doc, "4.3 Faltantes, dominios y normalización", "Heading 2")
    add_markup(
        doc,
        "Los 14 faltantes de `tld` no se imputaron. Trece son direcciones IP y uno es una URL malformada; en todos los casos `tld_len = 0`. Como `tld` no forma parte del conjunto primario, no se necesita una categoría artificial; si se usara como variable categórica, se codificaría como `sin_tld`. `tld_len` se conserva como predictor numérico porque no tiene faltantes.",
    )
    add_markup(
        doc,
        "Los 24 dominios con etiquetas contradictorias se conservaron. Después de la deduplicación agrupan 4 391 filas, el 3,81 % del conjunto. La decisión evita introducir una reetiquetación no respaldada y reconoce que un servicio legítimo puede alojar URL de phishing. La partición agrupada impide que un mismo dominio quede en dos particiones, incluso si contiene ambas clases.",
    )
    add_markup(
        doc,
        "Para agrupar, `dom` se normalizó a minúsculas, sin espacios exteriores, sin punto final y sin prefijo `www.` o `wwwN.`. Se obtuvieron 90 858 dominios normalizados. Esta columna se usa solo para definir grupos, no como predictor. `url`, `dom`, `dom_normalizado`, `tld` e `is_ip` quedaron fuera del conjunto primario: las tres primeras son identificadores o variables de alta cardinalidad, `tld` tiene 1 257 categorías observadas (1 258 si se cuenta `sin_tld`) y `is_ip` solo tiene 13 valores 1.",
    )
    add_markup(doc, "4.4 Conjunto de predictores", "Heading 2")
    add_markup(
        doc,
        "El conjunto primario contiene 21 variables numéricas, agrupadas en la Tabla 5. No hay faltantes en estos predictores, no se aplicó imputación y no se eliminaron valores extremos. La razón es que los máximos pueden ser URL reales y que el criterio IQR es poco informativo en variables discretas con muchos ceros.",
    )
    add_table(
        doc,
        "Tabla 5. Predictores primarios agrupados por tipo de información. Fuente: elaboración propia a partir de `results/tables/25_predictores_tratamiento.csv`.",
        ["Grupo", "Variables", "Interpretación"],
        [
            ["Longitud", "`url_len`, `dom_len`, `tld_len`, `path_len`, `query_len`", "Tamaño de la URL y sus componentes."],
            ["Conteos", "`letter_cnt`, `digit_cnt`, `special_cnt`, `eq_cnt`, `qm_cnt`, `amp_cnt`, `dot_cnt`, `dash_cnt`, `under_cnt`, `slash_cnt`, `subdom_cnt`", "Frecuencia de caracteres y elementos estructurales."],
            ["Proporciones", "`letter_ratio`, `digit_ratio`, `spec_ratio`", "Composición relativa de la URL."],
            ["Seguridad", "`is_https`", "Presencia de HTTPS; se conserva con cautela por posible artefacto."],
            ["Complejidad", "`entropy`", "Entropía de Shannon de la URL."],
        ],
        [17, 55, 28],
    )
    add_markup(
        doc,
        "La redundancia entre `url_len` y `letter_cnt`, y entre `eq_cnt` y `amp_cnt`, se conserva en el diseño inicial. En la Regresión Logística puede afectar la estabilidad de los coeficientes; en Random Forest y XGBoost puede repartir la importancia. Ninguna importancia se interpretará como causal. `is_https` se mantiene porque puede aportar información, pero se comparará con y sin ella en validación por su posible relación con el proceso de recolección.",
    )
    add_markup(doc, "4.5 Partición agrupada por dominio", "Heading 2")
    add_markup(
        doc,
        "Se compararon dos esquemas: una partición aleatoria estratificada por clase y una partición agrupada por `dom_normalizado`. La partición aleatoria produjo 1 653 dominios compartidos entre entrenamiento y prueba; esos dominios cubren 4 106 filas de prueba, el 23,75 % de esa partición. La partición agrupada no comparte filas, URL ni dominios entre particiones. Por esa razón se eligió la partición agrupada, con semilla `20261025` y proporciones 70/15/15.",
    )
    add_table(
        doc,
        "Tabla 6. Partición agrupada por dominio utilizada en el diseño. La última columna muestra el porcentaje sobre filas y sobre positivos de cada conjunto. Fuente: elaboración propia a partir de `results/tables/21_comparacion_particiones.csv` y `results/partition_audit.md`.",
        ["Partición", "Filas", "Clase 0", "Clase 1", "Tasa clase 1", "Dominios", "Dominio principal (filas; positivos)"],
        [
            ["Entrenamiento", "80 658", "69 044", "11 614", "14,399 %", "64 110", "pages.dev (1,30 %; 9,04 %)"],
            ["Validación", "17 291", "14 808", "2 483", "14,360 %", "13 722", "google.com (8,39 %; 57,95 %)"],
            ["Prueba", "17 282", "14 789", "2 493", "14,425 %", "13 026", "weebly.com (14,21 %; 98,03 %)"],
        ],
        [20, 10, 10, 10, 13, 10, 27],
        page_break=True,
    )
    add_markup(
        doc,
        "La partición conserva una proporción de clase 1 prácticamente idéntica en las tres partes: 14,399 %, 14,360 % y 14,425 %. El conjunto de prueba contiene 2 493 casos de phishing, pero **2 444 (98,03 %) pertenecen a `weebly.com`**; solo 49 positivos quedan fuera de ese dominio. La validación contiene 2 483 positivos, de los cuales **1 439 (57,95 %) son `google.com`**. El tamaño permite calcular las métricas, pero la evaluación no representa la masa de positivos del dataset: la prueba tiene 50 dominios positivos distintos y la validación 747, aunque uno de ellos domina cada conjunto. La partición es reproducible con los índices de `results/tables/20_particion_agrupada_indices.csv`.",
    )
    add_markup(
        doc,
        "La concentración es una consecuencia estructural de agrupar por dominio, no un error de la semilla. Al mantener 70/15/15 y no separar dominios, los grupos más grandes necesariamente ocupan una fracción decisiva de la evaluación. Por ello, las métricas globales de validación y prueba no deben interpretarse como generalización poblacional. Se recomienda reportar métricas por dominio y, si se autoriza, complementar con validación cruzada agrupada (`GroupKFold`). No se manipuló la partición para ocultar esa estructura.",
    )
    add_markup(doc, "4.6 Reglas de preprocesamiento para el modelado", "Heading 2")
    add_bullets(
        doc,
        [
            "Cualquier escalador, imputador, codificador o selección de variables que use información de los datos se ajustará solo con entrenamiento.",
            "La Regresión Logística usará `StandardScaler`; Random Forest y XGBoost no requieren escalado.",
            "No se aplicará imputación porque los 21 predictores no tienen faltantes.",
            "No se eliminarán valores extremos ni variables correlacionadas en el diseño inicial.",
            "El desbalance se tratará con pesos de clase; no se aplicará SMOTE antes de la partición.",
            "La prueba no se usará para elegir transformaciones, variables, hiperparámetros ni umbrales.",
        ],
    )
    add_markup(doc, "4.7 Limitaciones del preprocesamiento", "Heading 2")
    add_bullets(
        doc,
        [
            "La partición es aleatoria respecto de grupos, no temporal; no hay fecha de recolección por URL ni validación externa con otro dataset.",
            "La ficha de la fuente declara URL únicas y limpieza de duplicados, pero el archivo publicado contiene 1 369 duplicados exactos; el tamaño y el hash locales coinciden con los metadatos del archivo publicado.",
            "La prueba está dominada por `weebly.com` (98,03 % de los positivos) y la validación por `google.com` (57,95 %); las métricas globales no representan la masa de URL.",
            "Los dominios contradictorios y la concentración de dominios grandes pueden afectar la interpretación; además, `is_https` podría capturar un artefacto de recolección, y las características son solo de URL, sin contenido, certificado, reputación ni contexto de navegación.",
        ],
    )

    # 5. Model design
    add_markup(doc, "5. Diseño preliminar o selección del modelo", "Heading 1")
    add_markup(doc, "5.1 Alcance y criterios de diseño", "Heading 2")
    add_markup(
        doc,
        "Esta sección presenta un diseño, no una comparación experimental. Se eligieron tres candidatos que cubren una línea base lineal, un ensamble de árboles y un boosting de gradiente regularizado: Regresión Logística, Random Forest y XGBoost. Los tres son apropiados para datos tabulares y permiten comparar supuestos, interpretabilidad y costo computacional.",
    )
    add_markup(
        doc,
        "La Regresión Logística se incluye como línea base porque es rápida, reproducible e interpretable (Hastie et al., 2009). Random Forest captura interacciones y no linealidad y es robusto a la escala (Breiman, 2001). XGBoost incorpora boosting de gradiente con regularización (Chen & Guestrin, 2016). La implementación prevista usaría scikit-learn para los dos primeros modelos (Pedregosa et al., 2011).",
    )
    add_table(
        doc,
        "Tabla 7. Comparación conceptual de los modelos candidatos. Fuente: elaboración propia.",
        ["Modelo", "Idea", "Ventaja principal", "Limitación principal", "Dependencia"],
        [
            ["Regresión Logística", "Frontera lineal; línea base.", "Bajo costo e interpretabilidad.", "No captura interacciones sin transformaciones.", "`scikit-learn`"],
            ["Random Forest", "Ensamble de árboles; no lineal.", "Interacciones y robustez a escala.", "Mayor costo; importancia dispersa.", "`scikit-learn`"],
            ["XGBoost", "Boosting de gradiente regularizado.", "Interacciones con regularización.", "Más hiperparámetros; dependencia adicional.", "`xgboost` condicional"],
        ],
        [17, 25, 21, 23, 14],
    )
    add_markup(doc, "5.2 Modelos y configuraciones iniciales", "Heading 2")
    add_markup(doc, "5.2.1 Regresión Logística", "Heading 3")
    add_markup(
        doc,
        "Es la línea base. Permite comprobar cuánto se puede separar con una frontera lineal y sirve para evaluar si los modelos más complejos aportan una mejora real. Requiere estandarización. Se usa `class_weight=\"balanced\"` para dar más peso a la clase minoritaria; los coeficientes se interpretan en escala de log-odds, con cautela por la colinealidad.",
    )
    add_markup(doc, "5.2.2 Random Forest", "Heading 3")
    add_markup(
        doc,
        "Es un ensamble de árboles que reduce la varianza de un árbol individual y captura interacciones. No requiere escalado y es relativamente robusto a valores extremos. Se usa `class_weight=\"balanced_subsample\"`. La importancia de variables se interpretará con cautela porque las variables correlacionadas reparten su contribución.",
    )
    add_markup(doc, "5.2.3 XGBoost", "Heading 3")
    add_markup(
        doc,
        "Es un boosting de gradiente regularizado. Puede capturar interacciones y no linealidad, pero tiene más hiperparámetros y mayor costo de ajuste. Se propone `scale_pos_weight` calculado solo con la proporción de negativos y positivos del entrenamiento (aproximadamente 5,945). XGBoost **no está instalado** en el entorno; por tanto, el candidato queda diseñado pero condicionado a aprobación e instalación.",
    )
    add_table(
        doc,
        "Tabla 8. Configuraciones iniciales propuestas. No son resultados ni configuraciones optimizadas. Fuente: elaboración propia a partir de `results/model_design.md`.",
        ["Modelo", "Preprocesamiento", "Configuración inicial", "Pesos"],
        [
            [
                "Regresión Logística",
                "`StandardScaler` ajustado solo con entrenamiento.",
                "`penalty=\"l2\"`; `C=1.0`; `solver=\"lbfgs\"`; `max_iter=2000`; `random_state=20261025`.",
                "`class_weight = \"balanced\"`.",
            ],
            [
                "Random Forest",
                "Sin escalado.",
                "`n_estimators = 300`; `criterion = \"gini\"`; `max_depth = None`; `min_samples_leaf = 2`; `max_features = \"sqrt\"`; `bootstrap = True`; `n_jobs = -1`; `random_state = 20261025`.",
                "`class_weight = \"balanced_subsample\"`.",
            ],
            [
                "XGBoost",
                "Sin escalado.",
                "`n_estimators = 300`; `learning_rate = 0.05`; `max_depth = 6`; `min_child_weight = 1`; `subsample = 0.8`; `colsample_bytree = 0.8`; `reg_lambda = 1.0`; `objective = \"binary:logistic\"`; `eval_metric = \"aucpr\"`; `tree_method = \"hist\"`; `n_jobs = -1`; `random_state = 20261025`.",
                "`scale_pos_weight ≈ 5,945` (neg/pos de train).",
            ],
        ],
        [19, 20, 41, 20],
        font_size=8.0,
        page_break=True,
    )
    add_markup(
        doc,
        "No se usará `early_stopping` en la configuración inicial, para no incorporar validación al ajuste sin un protocolo explícito. Si se incorpora más adelante, el conjunto de evaluación debe ser validación y la prueba debe permanecer intacta. Si XGBoost no se autoriza o no es viable, no se reemplazará silenciosamente: se documentará la decisión y se pedirá una alternativa.",
    )
    add_markup(doc, "5.3 Métricas y protocolo de evaluación", "Heading 2")
    add_markup(
        doc,
        "Las métricas se calcularán en validación para comparar y en prueba una sola vez para el modelo final. La Tabla 9 resume su función. La métrica principal prevista es PR-AUC, complementada con recall de la clase 1, porque el desbalance hace que la curva precision-recall sea más informativa que ROC (Saito & Rehmsmeier, 2015). ROC-AUC se reporta como medida secundaria (Fawcett, 2006).",
    )
    add_table(
        doc,
        "Tabla 9. Métricas previstas y su función. Fuente: elaboración propia.",
        ["Métrica", "Qué mide", "Uso previsto"],
        [
            ["Recall de clase 1", "Proporción de casos de phishing detectados.", "Métrica crítica: un falso negativo puede exponer al usuario."],
            ["Precision de clase 1", "Proporción de alertas de phishing que son correctas.", "Estima la carga de falsas alarmas."],
            ["F1 de clase 1", "Media armónica de precision y recall.", "Resume el equilibrio entre ambas."],
            ["PR-AUC", "Área bajo la curva precision-recall.", "Métrica principal bajo desbalance."],
            ["ROC-AUC", "Área bajo la curva ROC.", "Medida secundaria; puede ser optimista."],
            ["Matriz de confusión", "Conteo de TP, TN, FP y FN.", "Muestra errores absolutos por tipo."],
            ["Tasa de positivos predichos", "Proporción de casos clasificados como phishing.", "Verifica la carga operativa del umbral."],
            ["Accuracy", "Proporción global de aciertos.", "No se usa para seleccionar; la clase benigna domina."],
        ],
        [19, 42, 39],
    )
    add_markup(doc, "El protocolo de selección será el siguiente:", "Text body", keep_with_next=True)
    add_numbered(
        doc,
        [
            "Verificar el hash del dataset, los índices de partición y los conteos de filas y clases.",
            "Reconstruir entrenamiento, validación y prueba con los índices de la Fase 3.",
            "Ajustar cada pipeline exclusivamente con entrenamiento.",
            "Predecir validación y calcular recall, precision, F1, PR-AUC, ROC-AUC y matriz de confusión.",
            "Comparar por mayor PR-AUC; desempatar por recall de clase 1, luego por F1 y finalmente por menor complejidad y costo.",
            "Elegir el umbral operativo solo con validación, maximizando F1 y revisando la curva precision-recall.",
            "Congelar modelo, umbral y transformaciones.",
            "Evaluar una sola vez en prueba y reportar el resultado sin volver a seleccionar.",
            "Registrar semillas, versiones, tiempos y configuración para reproducibilidad.",
        ],
    )
    add_markup(
        doc,
        "También se reportarán las métricas con umbral 0,5 para comparar los candidatos en igualdad de condiciones. El umbral operativo podrá ser distinto, pero se elegirá con validación y se congelará antes de prueba. No se ajustará el umbral con prueba ni se reportará el “mejor” resultado de múltiples umbrales evaluados en ese conjunto.",
    )
    add_markup(doc, "5.4 Análisis de sensibilidad previsto", "Heading 2")
    add_bullets(
        doc,
        [
            "Comparar el modelo con y sin `is_https` usando validación.",
            "Revisar errores por dominio, especialmente `google.com` y `weebly.com`.",
            "Evaluar `is_ip` solo como sensibilidad, ya que no está en el conjunto primario.",
            "Revisar calibración y el efecto de los pesos de clase sobre las probabilidades.",
            "Mantener la prueba para una sola evaluación del modelo y umbral seleccionados.",
            "Considerar `GroupKFold` agrupado por dominio como análisis de sensibilidad, solo si se autoriza la instalación de `scikit-learn`; no se ejecutó en esta fase y no reemplaza la partición de referencia.",
        ],
    )
    add_markup(doc, "5.5 Riesgos, limitaciones y decisiones pendientes", "Heading 2")
    add_bullets(
        doc,
        [
            "`scikit-learn` y `xgboost` no están instalados; la fase de entrenamiento requerirá autorización e instalación registrada.",
            "XGBoost es un candidato condicional y no debe sustituirse silenciosamente.",
            "La prueba está dominada por `weebly.com` (98,03 % de los positivos): las métricas globales no estiman la población y deben acompañarse de análisis por dominio.",
            "`GroupKFold` no se ejecutó; su viabilidad depende de la instalación autorizada de `scikit-learn` y de conservar los grupos por `dom_normalizado`.",
            "Los 24 dominios contradictorios pueden introducir ruido de etiqueta.",
            "La validación no es temporal y no hay validación externa.",
            "Las configuraciones son puntos de partida, no resultados optimizados.",
            "No existen métricas de entrenamiento que puedan presentarse como hallazgos.",
        ],
    )
    add_markup(doc, "5.6 Cierre del diseño", "Heading 2")
    add_markup(
        doc,
        "El diseño propone una comparación reproducible y sin fuga por dominio. **La Fase 4 queda ejecutada y pendiente de revisión; no se entrenó ni evaluó ningún modelo.** La partición actual se conserva como referencia; `GroupKFold` queda como alternativa de sensibilidad condicionada. Cualquier entrenamiento posterior requiere aprobación, dependencias instaladas y prueba reservada.",
    )



def start_or_connect():
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    url = "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
    try:
        ctx = resolver.resolve(url)
        return ctx, None
    except Exception:
        soffice = shutil.which("soffice")
        if not soffice:
            raise RuntimeError("No se encontró LibreOffice/soffice.")
        profile = Path(tempfile.mkdtemp(prefix="lo_apa_"))
        proc = subprocess.Popen(
            [
                soffice,
                "--headless",
                "--invisible",
                "--norestore",
                "--nologo",
                "--nodefault",
                "--accept=socket,host=localhost,port=2002;urp;",
                f"-env:UserInstallation={profile.as_uri()}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            time.sleep(0.5)
            try:
                ctx = resolver.resolve(url)
                return ctx, proc
            except Exception:
                continue
        proc.terminate()
        raise RuntimeError("No se pudo iniciar el servicio UNO de LibreOffice.")


def _prop(name, value):
    prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    prop.Name = name
    prop.Value = value
    return prop


def _load_desktop():
    ctx, launched = start_or_connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(DOCX.as_uri(), "_blank", 0, ())
    return desktop, doc, launched


def _close_desktop(desktop, doc, launched):
    doc.close(True)
    if launched:
        try:
            desktop.terminate()
        except Exception:
            pass


def _fix_index_links():
    with zipfile.ZipFile(DOCX, "r") as zin:
        items = [(info, zin.read(info.filename)) for info in zin.infolist()]
    tmp = DOCX.with_suffix(".tmp.docx")
    replaced = 0
    with zipfile.ZipFile(tmp, "w") as zout:
        for info, data in items:
            if info.filename == "word/document.xml":
                xml = data.decode("utf-8")
                xml, n_fig = re.subn(
                    r'w:anchor="Figura!(\d+)\|sequence"',
                    lambda m: f'w:anchor="figura_{int(m.group(1)) + 1}"',
                    xml,
                )
                xml, n_tab = re.subn(
                    r'w:anchor="Tabla!(\d+)\|sequence"',
                    lambda m: f'w:anchor="tabla_{int(m.group(1)) + 1}"',
                    xml,
                )
                if "|sequence" in xml:
                    raise RuntimeError("Quedaron anclas internas de secuencia sin corregir.")
                replaced = n_fig + n_tab
                data = xml.encode("utf-8")
            zout.writestr(info, data)
    tmp.replace(DOCX)
    if replaced != 15:
        raise RuntimeError(f"Se esperaban 15 enlaces de figuras/tablas; se corrigieron {replaced}.")
    print(f"Enlaces de índices corregidos: {replaced}")


def update_fields_and_export():
    desktop, doc, launched = _load_desktop()
    try:
        doc.refresh()
        indexes = doc.getDocumentIndexes()
        for _ in range(2):
            for i in range(indexes.getCount()):
                indexes.getByIndex(i).update()
            doc.refresh()
        doc.storeToURL(
            DOCX.as_uri(),
            (_prop("FilterName", "MS Word 2007 XML"), _prop("Overwrite", True)),
        )
    finally:
        _close_desktop(desktop, doc, launched)

    _fix_index_links()

    desktop, doc, launched = _load_desktop()
    try:
        doc.refresh()
        doc.storeToURL(
            PDF.as_uri(),
            (_prop("FilterName", "writer_pdf_Export"), _prop("Overwrite", True)),
        )
    finally:
        _close_desktop(desktop, doc, launched)


def main():
    global TABLE_NUMBER, FIGURE_NUMBER
    TABLE_NUMBER = 0
    FIGURE_NUMBER = 0
    REPORT.mkdir(parents=True, exist_ok=True)
    doc = Document()
    setup_document(doc)
    props = doc.core_properties
    props.title = "Análisis comparativo de algoritmos de aprendizaje automático para la detección de sitios web de phishing mediante características de las URL"
    props.subject = "Informe de avance de la segunda unidad de Inteligencia Artificial"
    props.author = "Estudiante del curso"
    props.comments = "Informe académico de avance: EDA, preprocesamiento, partición y diseño preliminar de modelos. No contiene entrenamiento ni métricas de rendimiento."
    props.keywords = "phishing, URL, aprendizaje automático, EDA, partición por dominio"
    add_cover(doc)
    add_indices(doc)
    build_body(doc)
    add_references(doc)
    doc.save(str(DOCX))
    print(f"DOCX inicial: {DOCX} ({DOCX.stat().st_size} bytes)")
    update_fields_and_export()
    print(f"DOCX final: {DOCX} ({DOCX.stat().st_size} bytes)")
    print(f"PDF temporal: {PDF} ({PDF.stat().st_size} bytes)")
    print(f"Tablas: {TABLE_NUMBER}; figuras: {FIGURE_NUMBER}")


if __name__ == "__main__":
    main()
