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


XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'


def test_use_references_element_in_defs_with_translation():
    body = '<defs><rect id="box" width="5" height="5" fill="red"/></defs><use href="#box" x="10" y="10"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(12, 12) == (255, 0, 0, 255)
    assert canvas.get_pixel(2, 2)[3] == 0


def test_use_supports_xlink_href():
    body = '<defs><rect id="box" width="5" height="5" fill="blue"/></defs><use xlink:href="#box" x="5"/>'
    canvas = render_svg(svg(body, f'{XLINK} width="20" height="20"'))
    assert canvas.get_pixel(7, 2) == (0, 0, 255, 255)
    assert canvas.get_pixel(2, 2)[3] == 0


def test_use_references_rendered_element_and_draws_it_twice():
    body = '<rect id="box" width="5" height="5" fill="red"/><use href="#box" x="10"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(2, 2) == (255, 0, 0, 255)
    assert canvas.get_pixel(12, 2) == (255, 0, 0, 255)
    assert canvas.get_pixel(7, 2)[3] == 0


def test_use_transform_applies_before_xy_translation():
    body = '<defs><rect id="box" width="2" height="2" fill="red"/></defs><use href="#box" x="2" y="2" transform="scale(2)"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(5, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(3, 3)[3] == 0
    assert canvas.get_pixel(9, 9)[3] == 0


def test_use_passes_inherited_presentation_attributes():
    body = (
        '<defs><g id="shape"><rect width="5" height="5"/><rect x="5" width="5" height="5" fill="lime"/></g></defs>'
        '<g fill="blue"><use href="#shape"/></g><use href="#shape" y="10" fill="red" opacity="0.5"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(2, 2) == (0, 0, 255, 255)
    assert canvas.get_pixel(7, 2) == (0, 255, 0, 255)
    red = canvas.get_pixel(2, 12)
    assert red[:3] == (255, 0, 0) and abs(red[3] - 128) <= 1


def test_use_display_none_is_skipped():
    body = '<defs><rect id="box" width="20" height="20"/></defs><use href="#box" display="none"/>'
    assert render_svg(svg(body)).get_pixel(5, 5)[3] == 0


def test_symbol_is_not_rendered_directly():
    body = '<symbol id="icon"><rect width="20" height="20" fill="red"/></symbol>'
    assert render_svg(svg(body)).get_pixel(5, 5)[3] == 0


def test_use_symbol_with_viewbox_scales_to_width_and_height():
    body = (
        '<defs><symbol id="icon" viewBox="0 0 2 2"><rect width="1" height="1" fill="red"/></symbol></defs>'
        '<use href="#icon" x="4" y="4" width="10" height="10"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(6, 6) == (255, 0, 0, 255)
    assert canvas.get_pixel(8, 8) == (255, 0, 0, 255)
    assert canvas.get_pixel(10, 10)[3] == 0
    assert canvas.get_pixel(3, 3)[3] == 0


def test_use_symbol_viewbox_meets_and_centres():
    body = (
        '<symbol id="icon" viewBox="0 0 10 10"><rect width="10" height="10" fill="red"/></symbol>'
        '<use href="#icon" width="20" height="10"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(2, 5)[3] == 0
    assert canvas.get_pixel(10, 5) == (255, 0, 0, 255)
    assert canvas.get_pixel(17, 5)[3] == 0


def test_use_symbol_defaults_to_full_viewport():
    body = '<symbol id="icon" viewBox="0 0 1 1"><rect width="1" height="1" fill="red"/></symbol><use href="#icon"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(1, 1) == (255, 0, 0, 255)
    assert canvas.get_pixel(18, 18) == (255, 0, 0, 255)


def test_use_symbol_without_viewbox_only_translates():
    body = '<symbol id="icon"><rect width="4" height="4" fill="red"/></symbol><use href="#icon" x="10" y="10" width="2" height="2"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(12, 12) == (255, 0, 0, 255)
    assert canvas.get_pixel(5, 5)[3] == 0


def test_use_symbol_with_zero_width_draws_nothing():
    body = '<symbol id="icon" viewBox="0 0 1 1"><rect width="1" height="1" fill="red"/></symbol><use href="#icon" width="0"/>'
    assert render_svg(svg(body)).get_pixel(5, 5)[3] == 0


def test_nested_use_chain():
    body = (
        '<defs><rect id="a" width="2" height="2" fill="red"/><use id="b" href="#a" x="4"/></defs>'
        '<use href="#b" x="4"/>'
    )
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(9, 1) == (255, 0, 0, 255)
    assert canvas.get_pixel(5, 1)[3] == 0


def test_use_with_missing_or_external_reference_is_ignored():
    body = '<use href="#missing"/><use href="other.svg#box"/><use/><rect x="10" width="5" height="5" fill="red"/>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(12, 2) == (255, 0, 0, 255)
    assert canvas.get_pixel(2, 2)[3] == 0


def test_use_self_reference_raises():
    with pytest.raises(SVGError, match="circular"):
        render_svg(svg('<use id="loop" href="#loop"/>'))


def test_use_reference_cycle_raises():
    body = '<defs><g id="a"><use href="#b"/></g><g id="b"><use href="#a"/></g></defs><use href="#a"/>'
    with pytest.raises(SVGError, match="circular"):
        render_svg(svg(body))


def test_use_referencing_its_own_ancestor_raises():
    with pytest.raises(SVGError, match="circular"):
        render_svg(svg('<g id="outer"><rect width="2" height="2"/><use href="#outer" x="3"/></g>'))


def test_use_nesting_deeper_than_limit_is_refused():
    chain = '<rect id="u0" width="1" height="1"/>' + "".join(f'<use id="u{index}" href="#u{index - 1}"/>' for index in range(1, 40))
    with pytest.raises(UnsafeSVGError, match="depth"):
        render_svg(svg(f"<defs>{chain}</defs><use href='#u39'/>"))


def test_use_nesting_within_limit_renders():
    chain = '<rect id="u0" width="1" height="1" fill="red"/>' + "".join(f'<use id="u{index}" href="#u{index - 1}"/>' for index in range(1, 30))
    canvas = render_svg(svg(f"<defs>{chain}</defs><use href='#u29'/>"))
    assert canvas.get_pixel(0, 0) == (255, 0, 0, 255)


def test_exponential_use_expansion_is_refused():
    levels = ['<rect id="l0" width="1" height="1"/>']
    for level in range(1, 12):
        uses = "".join(f'<use href="#l{level - 1}"/>' for _ in range(10))
        levels.append(f'<g id="l{level}">{uses}</g>')
    with pytest.raises(UnsafeSVGError, match="expan"):
        render_svg(svg(f"<defs>{''.join(levels)}</defs><use href='#l11'/>"))


POLYLINE_CORNER = '<polyline points="4 4 16 4 16 16" fill="none" stroke="red" stroke-width="4"{}/>'
SEGMENT = '<line x1="4" y1="10" x2="16" y2="10" stroke="red" stroke-width="4"{}/>'


def test_svg_default_linecap_is_butt():
    canvas = render_svg(svg(SEGMENT.format("")))
    assert canvas.get_pixel(4, 10) == (255, 0, 0, 255)
    assert canvas.get_pixel(3, 10)[3] == 0
    assert canvas.get_pixel(16, 10)[3] == 0


def test_svg_linecap_round_and_square():
    round_canvas = render_svg(svg(SEGMENT.format(' stroke-linecap="round"')))
    assert round_canvas.get_pixel(3, 10) == (255, 0, 0, 255)
    assert round_canvas.get_pixel(1, 10)[3] == 0
    square_canvas = render_svg(svg(SEGMENT.format(' style="stroke-linecap: square"')))
    assert square_canvas.get_pixel(2, 8) == (255, 0, 0, 255)
    assert square_canvas.get_pixel(1, 10)[3] == 0


def test_svg_default_linejoin_is_miter():
    canvas = render_svg(svg(POLYLINE_CORNER.format("")))
    assert canvas.get_pixel(17, 2) == (255, 0, 0, 255)


def test_svg_linejoin_bevel_and_round():
    assert render_svg(svg(POLYLINE_CORNER.format(' stroke-linejoin="bevel"'))).get_pixel(17, 2)[3] == 0
    assert 0 < render_svg(svg(POLYLINE_CORNER.format(' stroke-linejoin="round"'))).get_pixel(17, 2)[3] < 255


def test_svg_miterlimit_falls_back_to_bevel():
    assert render_svg(svg(POLYLINE_CORNER.format(' stroke-miterlimit="1.2"'))).get_pixel(17, 2)[3] == 0
    assert render_svg(svg(POLYLINE_CORNER.format(' stroke-miterlimit="2"'))).get_pixel(17, 2)[3] == 255


def test_svg_stroke_line_properties_are_inherited():
    body = f'<g stroke-linejoin="bevel" stroke-linecap="round">{POLYLINE_CORNER.format("")}</g>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(17, 2)[3] == 0
    assert canvas.get_pixel(3, 4) == (255, 0, 0, 255)


def test_svg_invalid_stroke_line_values_are_ignored():
    invalid = POLYLINE_CORNER.format(' stroke-linejoin="spiky" stroke-miterlimit="0.5" stroke-linecap="flat"')
    body = f'<g stroke-linejoin="bevel">{invalid}</g>'
    canvas = render_svg(svg(body))
    assert canvas.get_pixel(17, 2)[3] == 0
    assert canvas.get_pixel(3, 4)[3] == 0
