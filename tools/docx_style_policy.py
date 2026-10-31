from __future__ import annotations

import copy
import io
import re
import zipfile
from pathlib import Path

from lxml import etree


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"
NS = {"w": WORD_NS}

FONT_NAME = "Times New Roman"
BODY_SIZE_HALF_POINTS = "28"
TABLE_SIZE_HALF_POINTS = "24"
FIRST_LINE_TWIPS = "709"
SINGLE_LINE_TWIPS = "240"
BLACK = "000000"
FORBIDDEN_DASHES = "\u2013\u2014"

STORY_PATTERN = re.compile(
    r"word/(?:document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$"
)
HEADING_NAME_PATTERN = re.compile(
    r"(?:heading|заголовок)\s*[1-9]|title|subtitle|название|подзаголовок",
    re.IGNORECASE,
)
NUMBERED_HEADING_PATTERN = re.compile(r"^\s*\d+(?:\.\d+){0,5}\s+\S")


def _child(parent: etree._Element, local_name: str) -> etree._Element:
    tag = W + local_name
    node = parent.find(tag)
    if node is None:
        node = etree.Element(tag)
        if local_name in {"pPr", "rPr"}:
            parent.insert(0, node)
        else:
            parent.append(node)
    return node


def _set_fonts(r_pr: etree._Element) -> None:
    fonts = _child(r_pr, "rFonts")
    for key in list(fonts.attrib):
        if key.lower().endswith("theme"):
            del fonts.attrib[key]
    for key in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(W + key, FONT_NAME)


def _set_size(r_pr: etree._Element, half_points: str) -> None:
    _child(r_pr, "sz").set(W + "val", half_points)
    _child(r_pr, "szCs").set(W + "val", half_points)


def _set_bold(r_pr: etree._Element, enabled: bool) -> None:
    for name in ("b", "bCs"):
        node = _child(r_pr, name)
        node.set(W + "val", "1" if enabled else "0")


def _set_black(r_pr: etree._Element) -> None:
    color = _child(r_pr, "color")
    for key in list(color.attrib):
        del color.attrib[key]
    color.set(W + "val", BLACK)


def _remove_child(parent: etree._Element, local_name: str) -> None:
    for node in parent.findall(W + local_name):
        parent.remove(node)


def _set_paragraph_properties(
    paragraph: etree._Element,
    in_table: bool,
    heading: bool,
) -> None:
    p_pr = _child(paragraph, "pPr")
    ind = _child(p_pr, "ind")
    for key in ("firstLineChars", "hanging", "hangingChars"):
        ind.attrib.pop(W + key, None)
    ind.set(W + "left", "0")
    ind.set(W + "right", "0")
    if in_table:
        ind.set(W + "firstLine", "0")
        ind.set(W + "firstLineChars", "0")
    else:
        ind.set(W + "firstLine", FIRST_LINE_TWIPS)
        _remove_child(p_pr, "pBdr")

    spacing = _child(p_pr, "spacing")
    for key in list(spacing.attrib):
        del spacing.attrib[key]
    spacing.set(W + "before", "0")
    spacing.set(W + "after", "0")
    spacing.set(W + "line", SINGLE_LINE_TWIPS)
    spacing.set(W + "lineRule", "auto")
    _child(p_pr, "jc").set(W + "val", "both")

    mark_r_pr = _child(p_pr, "rPr")
    _set_fonts(mark_r_pr)
    _set_black(mark_r_pr)
    _set_size(
        mark_r_pr,
        TABLE_SIZE_HALF_POINTS if in_table else BODY_SIZE_HALF_POINTS,
    )
    if heading:
        _set_bold(mark_r_pr, True)


def _style_maps(styles: etree._Element) -> tuple[set[str], set[str]]:
    headings: set[str] = set()
    table_styles: set[str] = set()
    for style in styles.findall("w:style", NS):
        style_id = style.get(W + "styleId", "")
        style_type = style.get(W + "type", "")
        name = style.find("w:name", NS)
        label = name.get(W + "val", "") if name is not None else ""
        if style_type == "table":
            table_styles.add(style_id)
        if style_type == "paragraph" and (
            HEADING_NAME_PATTERN.fullmatch(label.strip())
            or style_id.lower() in {"title", "subtitle"}
        ):
            headings.add(style_id)
    return headings, table_styles


def _paragraph_is_heading(
    paragraph: etree._Element,
    heading_style_ids: set[str],
) -> bool:
    p_style = paragraph.find("w:pPr/w:pStyle", NS)
    if p_style is not None and p_style.get(W + "val", "") in heading_style_ids:
        return True
    if paragraph.find("w:pPr/w:outlineLvl", NS) is not None:
        return True
    text = "".join(paragraph.itertext()).strip()
    return bool(text and len(text) <= 180 and NUMBERED_HEADING_PATTERN.match(text))


def _in_table(node: etree._Element) -> bool:
    current = node.getparent()
    while current is not None:
        if current.tag == W + "tbl":
            return True
        current = current.getparent()
    return False


def _format_style(style: etree._Element, heading: bool, table_style: bool) -> None:
    r_pr = _child(style, "rPr")
    _set_fonts(r_pr)
    _set_black(r_pr)
    _set_size(
        r_pr,
        TABLE_SIZE_HALF_POINTS if table_style else BODY_SIZE_HALF_POINTS,
    )
    if heading:
        _set_bold(r_pr, True)
    if style.get(W + "type") == "paragraph":
        p_pr = _child(style, "pPr")
        _remove_child(p_pr, "pBdr")
        ind = _child(p_pr, "ind")
        ind.set(W + "left", "0")
        ind.set(W + "right", "0")
        ind.set(W + "firstLine", FIRST_LINE_TWIPS)
        spacing = _child(p_pr, "spacing")
        spacing.set(W + "before", "0")
        spacing.set(W + "after", "0")
        spacing.set(W + "line", SINGLE_LINE_TWIPS)
        spacing.set(W + "lineRule", "auto")
        _child(p_pr, "jc").set(W + "val", "both")


def _replace_forbidden_dashes(root: etree._Element) -> int:
    replacements = 0
    translation = str.maketrans({"\u2013": "-", "\u2014": "-"})
    for node in root.findall(".//w:t", NS):
        text = node.text or ""
        count = sum(text.count(char) for char in FORBIDDEN_DASHES)
        if count:
            node.text = text.translate(translation)
            replacements += count
    return replacements


def _format_story(
    root: etree._Element,
    heading_style_ids: set[str],
) -> tuple[int, int, int]:
    paragraph_count = 0
    heading_count = 0
    table_paragraph_count = 0
    for paragraph in root.findall(".//w:p", NS):
        paragraph_count += 1
        in_table = _in_table(paragraph)
        heading = _paragraph_is_heading(paragraph, heading_style_ids)
        if in_table:
            table_paragraph_count += 1
        if heading:
            heading_count += 1
        _set_paragraph_properties(paragraph, in_table, heading)
        half_points = (
            TABLE_SIZE_HALF_POINTS if in_table else BODY_SIZE_HALF_POINTS
        )
        for run in paragraph.findall(".//w:r", NS):
            r_pr = _child(run, "rPr")
            _set_fonts(r_pr)
            _set_black(r_pr)
            _set_size(r_pr, half_points)
            if heading:
                _set_bold(r_pr, True)
    return paragraph_count, heading_count, table_paragraph_count


def transform_docx(data: bytes, version: str | None = None) -> tuple[bytes, dict]:
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        members = {info.filename: source.read(info.filename) for info in source.infolist()}
        infos = {info.filename: copy.copy(info) for info in source.infolist()}

    styles = etree.fromstring(members["word/styles.xml"])
    heading_style_ids, table_style_ids = _style_maps(styles)
    for style in styles.findall("w:style", NS):
        style_id = style.get(W + "styleId", "")
        _format_style(
            style,
            style_id in heading_style_ids,
            style_id in table_style_ids,
        )
    members["word/styles.xml"] = etree.tostring(
        styles,
        encoding="UTF-8",
        xml_declaration=True,
        standalone=True,
    )

    paragraphs = 0
    headings = 0
    table_paragraphs = 0
    dash_replacements = 0
    story_parts = []
    for name in sorted(members):
        if not STORY_PATTERN.fullmatch(name):
            continue
        root = etree.fromstring(members[name])
        dash_replacements += _replace_forbidden_dashes(root)
        counts = _format_story(root, heading_style_ids)
        paragraphs += counts[0]
        headings += counts[1]
        table_paragraphs += counts[2]
        members[name] = etree.tostring(
            root,
            encoding="UTF-8",
            xml_declaration=True,
            standalone=True,
        )
        story_parts.append(name)

    if version is not None and "docProps/core.xml" in members:
        core = etree.fromstring(members["docProps/core.xml"])
        core_ns = (
            "{http://schemas.openxmlformats.org/package/2006/metadata/"
            "core-properties}version"
        )
        node = core.find(core_ns)
        if node is None:
            node = etree.SubElement(core, core_ns)
        node.text = version
        members["docProps/core.xml"] = etree.tostring(
            core,
            encoding="UTF-8",
            xml_declaration=True,
            standalone=True,
        )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for name, payload in members.items():
            target.writestr(infos[name], payload)
    result = output.getvalue()
    audit = audit_docx(result)
    if audit["status"] != "PASS":
        raise ValueError(f"DOCX style policy failed: {audit}")
    return result, {
        "paragraphs": paragraphs,
        "headings": headings,
        "table_paragraphs": table_paragraphs,
        "dash_replacements": dash_replacements,
        "story_parts": story_parts,
        "audit": audit,
    }


def _run_is_formatted(
    run: etree._Element,
    half_points: str,
    bold_required: bool,
) -> bool:
    r_pr = run.find("w:rPr", NS)
    if r_pr is None:
        return False
    fonts = r_pr.find("w:rFonts", NS)
    if fonts is None or any(
        fonts.get(W + key) != FONT_NAME
        for key in ("ascii", "hAnsi", "eastAsia", "cs")
    ):
        return False
    if any(key.lower().endswith("theme") for key in fonts.attrib):
        return False
    color = r_pr.find("w:color", NS)
    if color is None or color.get(W + "val", "").upper() != BLACK:
        return False
    if any(
        key.lower().endswith(("themecolor", "themetint", "themeshade"))
        for key in color.attrib
    ):
        return False
    for name in ("sz", "szCs"):
        node = r_pr.find("w:" + name, NS)
        if node is None or node.get(W + "val") != half_points:
            return False
    if bold_required:
        for name in ("b", "bCs"):
            node = r_pr.find("w:" + name, NS)
            if node is None or node.get(W + "val") not in {"1", "true", "on"}:
                return False
    return True


def audit_docx(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        styles = etree.fromstring(source.read("word/styles.xml"))
        heading_style_ids, _ = _style_maps(styles)
        names = [name for name in source.namelist() if STORY_PATTERN.fullmatch(name)]
        roots = [(name, etree.fromstring(source.read(name))) for name in names]

    failures = []
    style_count = 0
    for index, style in enumerate(styles.findall("w:style", NS), start=1):
        style_count += 1
        r_pr = style.find("w:rPr", NS)
        if r_pr is None:
            failures.append(f"styles.xml:style{index}:missing run property")
        else:
            color = r_pr.find("w:color", NS)
            if color is None or color.get(W + "val", "").upper() != BLACK:
                failures.append(f"styles.xml:style{index}:text color")
            elif any(
                key.lower().endswith(("themecolor", "themetint", "themeshade"))
                for key in color.attrib
            ):
                failures.append(f"styles.xml:style{index}:theme text color")
        if (
            style.get(W + "type") == "paragraph"
            and style.find("w:pPr/w:pBdr", NS) is not None
        ):
            failures.append(f"styles.xml:style{index}:paragraph border")
    paragraph_count = 0
    table_paragraph_count = 0
    heading_count = 0
    text_run_count = 0
    dash_count = 0
    for part_name, root in roots:
        dash_count += sum(
            sum((node.text or "").count(char) for char in FORBIDDEN_DASHES)
            for node in root.findall(".//w:t", NS)
        )
        for index, paragraph in enumerate(root.findall(".//w:p", NS), start=1):
            paragraph_count += 1
            in_table = _in_table(paragraph)
            heading = _paragraph_is_heading(paragraph, heading_style_ids)
            table_paragraph_count += int(in_table)
            heading_count += int(heading)
            p_pr = paragraph.find("w:pPr", NS)
            ind = paragraph.find("w:pPr/w:ind", NS)
            spacing = paragraph.find("w:pPr/w:spacing", NS)
            jc = paragraph.find("w:pPr/w:jc", NS)
            if p_pr is None or ind is None or spacing is None or jc is None:
                failures.append(f"{part_name}:p{index}:missing paragraph property")
                continue
            if in_table:
                indent_ok = (
                    ind.get(W + "left") == "0"
                    and ind.get(W + "right") == "0"
                    and ind.get(W + "firstLine") == "0"
                    and ind.get(W + "firstLineChars") == "0"
                )
            else:
                indent_ok = (
                    ind.get(W + "left") == "0"
                    and ind.get(W + "right") == "0"
                    and ind.get(W + "firstLine") == FIRST_LINE_TWIPS
                )
            if not indent_ok:
                failures.append(f"{part_name}:p{index}:indent")
            if not in_table and paragraph.find("w:pPr/w:pBdr", NS) is not None:
                failures.append(f"{part_name}:p{index}:paragraph border")
            if not (
                spacing.get(W + "before") == "0"
                and spacing.get(W + "after") == "0"
                and spacing.get(W + "line") == SINGLE_LINE_TWIPS
                and spacing.get(W + "lineRule") == "auto"
            ):
                failures.append(f"{part_name}:p{index}:spacing")
            if jc.get(W + "val") != "both":
                failures.append(f"{part_name}:p{index}:justification")
            expected_size = (
                TABLE_SIZE_HALF_POINTS if in_table else BODY_SIZE_HALF_POINTS
            )
            for run_index, run in enumerate(paragraph.findall(".//w:r", NS), start=1):
                if not run.findall(".//w:t", NS):
                    continue
                text_run_count += 1
                if not _run_is_formatted(run, expected_size, heading):
                    failures.append(
                        f"{part_name}:p{index}:r{run_index}:run formatting"
                    )
    if dash_count:
        failures.append(f"forbidden dash characters:{dash_count}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "styles": style_count,
        "paragraphs": paragraph_count,
        "table_paragraphs": table_paragraph_count,
        "headings": heading_count,
        "text_runs": text_run_count,
        "forbidden_dashes": dash_count,
        "failures": failures[:100],
    }


def format_file(source: Path, target: Path, version: str | None = None) -> dict:
    payload, report = transform_docx(source.read_bytes(), version=version)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return report
