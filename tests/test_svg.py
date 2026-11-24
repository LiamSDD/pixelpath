import pytest

from pixelpath import render_svg
from pixelpath.svg import SVGError, UnsafeSVGError

NS = 'xmlns="http://www.w3.org/2000/svg"'


def svg(body, attributes='width="20" height="20"'):
    return f"<svg {NS} {attributes}>{body}</svg>"


def test_basic_rect_and_size():
    canvas = render_svg(svg('<rect width="10" height="10" fill="red"/>'))
    assert (canvas.width, canvas.height) == (20, 20)
    assert canvas.get_pixel(5, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(15, 15) == (0, 0, 0, 0)


def test_default_fill_is_black():
    canvas = render_svg(svg('<rect width="10" height="10"/>'))
    assert canvas.get_pixel(5, 5) == (0, 0, 0, 255)


def test_svg_without_namespace_is_accepted():
    canvas = render_svg('<svg width="4" height="4"><rect width="4" height="4" fill="blue"/></svg>')
    assert canvas.get_pixel(2, 2) == (0, 0, 255, 255)


def test_viewbox_scales_content():
    canvas = render_svg(svg('<rect width="5" height="5" fill="red"/>', 'width="100" height="100" viewBox="0 0 10 10"'))
    assert canvas.get_pixel(25, 25) == (255, 0, 0, 255)
    assert canvas.get_pixel(75, 75)[3] == 0


def test_viewbox_offset():
    canvas = render_svg(svg('<rect x="10" y="10" width="5" height="5" fill="red"/>', 'viewBox="10 10 10 10" width="10" height="10"'))
    assert canvas.get_pixel(2, 2) == (255, 0, 0, 255)
    assert canvas.get_pixel(7, 7)[3] == 0


def test_size_defaults_to_viewbox():
    canvas = render_svg(svg("", 'viewBox="0 0 30 15"'))
    assert (canvas.width, canvas.height) == (30, 15)


def test_size_defaults_without_viewbox_or_dimensions():
    canvas = render_svg(svg("", ""))
    assert (canvas.width, canvas.height) == (300, 150)


def test_units_on_root_dimensions():
    canvas = render_svg(svg("", 'width="12px" height="0.25in"'))
    assert (canvas.width, canvas.height) == (12, 24)


def test_width_override_keeps_aspect_ratio():
    canvas = render_svg(svg("", 'viewBox="0 0 20 10"'), width=40)
    assert (canvas.width, canvas.height) == (40, 20)


def test_height_override_keeps_aspect_ratio():
    canvas = render_svg(svg("", 'viewBox="0 0 20 10"'), height=30)
    assert (canvas.width, canvas.height) == (60, 30)


def test_scale_override():
    canvas = render_svg(svg('<rect width="10" height="10" fill="red"/>'), scale=2)
    assert (canvas.width, canvas.height) == (40, 40)
    assert canvas.get_pixel(15, 15) == (255, 0, 0, 255)
    assert canvas.get_pixel(25, 25)[3] == 0


def test_meet_letterboxes_and_centers():
    canvas = render_svg(svg('<rect width="10" height="10" fill="red"/>', 'viewBox="0 0 10 10"'), width=20, height=10)
    assert canvas.get_pixel(2, 5)[3] == 0
    assert canvas.get_pixel(10, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(17, 5)[3] == 0


def test_background_option():
    canvas = render_svg(svg(""), background="white")
    assert canvas.get_pixel(0, 0) == (255, 255, 255, 255)


def test_group_fill_inheritance_and_override():
    body = '<g fill="blue"><rect width="10" height="10"/><rect x="10" width="10" height="10" fill="lime"/></g>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(5, 5) == (0, 0, 255, 255)
    assert canvas.get_pixel(15, 5) == (0, 255, 0, 255)


def test_nested_group_transforms_compose():
    body = '<g transform="translate(10,0)"><g transform="scale(0.5)"><rect width="10" height="10" fill="red"/></g></g>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(12, 2) == (255, 0, 0, 255)
    assert canvas.get_pixel(2, 2)[3] == 0
    assert canvas.get_pixel(17, 2)[3] == 0


def test_element_transform():
    canvas = render_svg(svg('<rect width="4" height="4" fill="red" transform="translate(10 10)"/>'))
    assert canvas.get_pixel(12, 12) == (255, 0, 0, 255)
    assert canvas.get_pixel(2, 2)[3] == 0


def test_fill_opacity_is_inherited_and_opacity_multiplies():
    canvas = render_svg(svg('<g fill-opacity="0.5"><rect width="10" height="10"/></g>'))
    assert abs(canvas.get_pixel(5, 5)[3] - 128) <= 1
    canvas = render_svg(svg('<g opacity="0.5"><rect width="10" height="10" opacity="0.5"/></g>'))
    assert abs(canvas.get_pixel(5, 5)[3] - 64) <= 1


def test_fill_rule_is_inherited():
    ring = '<path d="M0 0 H20 V20 H0 Z M5 5 H15 V15 H5 Z"/>'
    assert render_svg(svg(ring)).get_pixel(10, 10)[3] == 255
    assert render_svg(svg(f'<g fill-rule="evenodd">{ring}</g>')).get_pixel(10, 10)[3] == 0


def test_style_attribute_overrides_presentation_attribute():
    canvas = render_svg(svg('<rect width="10" height="10" fill="red" style="fill: blue; fill-opacity:1"/>'))
    assert canvas.get_pixel(5, 5) == (0, 0, 255, 255)


def test_circle_ellipse_polygon():
    body = (
        '<circle cx="5" cy="5" r="4" fill="red"/>'
        '<ellipse cx="15" cy="5" rx="4" ry="2" fill="lime"/>'
        '<polygon points="0,12 8,12 8,20 0,20" fill="blue"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(5, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(15, 5) == (0, 255, 0, 255)
    assert canvas.get_pixel(15, 8)[3] == 0
    assert canvas.get_pixel(4, 16) == (0, 0, 255, 255)


def test_polyline_fills_closed_and_strokes_open():
    body = '<polyline points="2 2 18 2 18 18" fill="red" stroke="blue" stroke-width="2"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(14, 6)[:3] == (255, 0, 0)
    assert canvas.get_pixel(10, 2)[:3] == (0, 0, 255)
    assert canvas.get_pixel(5, 15)[3] == 0


def test_line_is_stroked_only():
    canvas = render_svg(svg('<line x1="0" y1="10" x2="20" y2="10" stroke="red" stroke-width="4"/>'))
    assert canvas.get_pixel(10, 10) == (255, 0, 0, 255)
    assert canvas.get_pixel(10, 3)[3] == 0
    assert render_svg(svg('<line x1="0" y1="10" x2="20" y2="10"/>')).get_pixel(10, 10)[3] == 0


def test_stroke_on_shape_with_no_fill():
    canvas = render_svg(svg('<rect x="4" y="4" width="12" height="12" fill="none" stroke="red" stroke-width="2"/>'))
    assert canvas.get_pixel(4, 10) == (255, 0, 0, 255)
    assert canvas.get_pixel(10, 10)[3] == 0


def test_stroke_width_inherited_and_stroke_opacity():
    canvas = render_svg(svg('<g stroke="black" stroke-width="6" stroke-opacity="0.5"><line x1="0" y1="10" x2="20" y2="10"/></g>'))
    assert abs(canvas.get_pixel(10, 8)[3] - 128) <= 1


def test_rounded_rect_with_rx_and_ry():
    canvas = render_svg(svg('<rect width="20" height="20" rx="8" fill="red"/>'))
    assert canvas.get_pixel(0, 0)[3] == 0
    assert canvas.get_pixel(10, 10) == (255, 0, 0, 255)
    canvas = render_svg(svg('<rect width="20" height="20" ry="8" fill="red"/>'))
    assert canvas.get_pixel(0, 0)[3] == 0


def test_current_color_uses_color_property():
    canvas = render_svg(svg('<g color="lime"><rect width="10" height="10" fill="currentColor"/></g>'))
    assert canvas.get_pixel(5, 5) == (0, 255, 0, 255)


def test_display_none_and_visibility_hidden_are_skipped():
    canvas = render_svg(svg('<g display="none"><rect width="20" height="20"/></g><rect width="20" height="20" visibility="hidden"/>'))
    assert canvas.get_pixel(5, 5)[3] == 0


def test_unsupported_elements_are_ignored():
    body = (
        '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient>'
        '<rect id="hidden" width="20" height="20" fill="red"/></defs>'
        '<text x="0" y="10">hello</text><filter id="f"/><mask id="m"/><title>t</title>'
        '<rect width="10" height="10" fill="url(#g)"/>'
        '<rect x="10" width="10" height="10" fill="url(#g) blue"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(5, 5)[3] == 0
    assert canvas.get_pixel(15, 5) == (0, 0, 255, 255)
    assert canvas.get_pixel(5, 15)[3] == 0


def test_percentage_lengths_resolve_against_viewbox():
    canvas = render_svg(svg('<rect width="50%" height="100%" fill="red"/>', 'viewBox="0 0 20 10"'))
    assert canvas.get_pixel(5, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(15, 5)[3] == 0


def test_render_from_file_path_and_bytes(tmp_path):
    source = svg('<rect width="20" height="20" fill="red"/>')
    target = tmp_path / "image.svg"
    target.write_text(source, encoding="utf-8")
    assert render_svg(target).get_pixel(1, 1) == (255, 0, 0, 255)
    assert render_svg(str(target)).get_pixel(1, 1) == (255, 0, 0, 255)
    assert render_svg(source.encode("utf-8")).get_pixel(1, 1) == (255, 0, 0, 255)


def test_xml_declaration_is_allowed():
    canvas = render_svg('<?xml version="1.0" encoding="UTF-8"?>' + svg('<rect width="20" height="20"/>'))
    assert canvas.get_pixel(1, 1)[3] == 255


XXE = (
    '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    f'<svg {NS} width="10" height="10"><text>&xxe;</text></svg>'
)

BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>'
    f'<svg {NS}><text>&lol2;</text></svg>'
)


@pytest.mark.parametrize(
    "document",
    [
        XXE,
        BILLION_LAUGHS,
        f'<!doctype svg><svg {NS}/>',
        f'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg {NS}/>',
    ],
)
def test_doctype_and_entity_declarations_are_refused(document):
    with pytest.raises(UnsafeSVGError, match="DOCTYPE|ENTITY"):
        render_svg(document)


def test_refusal_works_for_bytes_and_other_encodings():
    with pytest.raises(UnsafeSVGError):
        render_svg(XXE.encode("utf-8"))
    with pytest.raises(UnsafeSVGError):
        render_svg(XXE.replace('version="1.0"', 'version="1.0" encoding="UTF-16"').encode("utf-16"))


def test_refusal_works_for_files(tmp_path):
    target = tmp_path / "evil.svg"
    target.write_text(XXE, encoding="utf-8")
    with pytest.raises(UnsafeSVGError):
        render_svg(target)


def test_unsafe_error_is_svg_error():
    assert issubclass(UnsafeSVGError, SVGError)
    assert issubclass(SVGError, ValueError)


def test_malformed_xml_raises_svg_error():
    with pytest.raises(SVGError):
        render_svg("<svg><rect></svg>")


def test_non_svg_root_raises():
    with pytest.raises(SVGError):
        render_svg("<html><body/></html>")


def test_invalid_path_data_raises_svg_error():
    with pytest.raises(SVGError):
        render_svg(svg('<path d="L 10 10"/>'))


def test_conflicting_size_options_raise():
    with pytest.raises(ValueError):
        render_svg(svg(""), width=10, scale=2)
