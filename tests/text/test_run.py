# pyright: reportPrivateUsage=false

"""Test suite for the docx.text.run module."""

from __future__ import annotations

from typing import Any, List, cast

import pytest

from skelmis.docx import types as t
from skelmis.docx.enum.style import WD_STYLE_TYPE
from skelmis.docx.enum.text import WD_BREAK, WD_UNDERLINE
from skelmis.docx.oxml.text.run import CT_R
from skelmis.docx.parts.document import DocumentPart
from skelmis.docx.shape import InlineShape
from skelmis.docx.text.font import Font
from skelmis.docx.text.run import Run

from ..unitutil.cxml import element, xml
from ..unitutil.mock import class_mock, instance_mock, property_mock


class DescribeRun:
    """Unit-test suite for `docx.text.run.Run`."""

    def it_knows_its_bool_prop_states(self, bool_prop_get_fixture):
        run, prop_name, expected_state = bool_prop_get_fixture
        assert getattr(run, prop_name) == expected_state

    def it_can_change_its_bool_prop_settings(self, bool_prop_set_fixture):
        run, prop_name, value, expected_xml = bool_prop_set_fixture
        setattr(run, prop_name, value)
        assert run._r.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", False),
            ('w:r/w:t"foobar"', False),
            ('w:r/(w:t"abc", w:lastRenderedPageBreak, w:t"def")', True),
            ("w:r/(w:lastRenderedPageBreak, w:lastRenderedPageBreak)", True),
        ],
    )
    def it_knows_whether_it_contains_a_page_break(self, r_cxml: str, expected_value: bool):
        r = cast(CT_R, element(r_cxml))
        run = Run(r, None)  # pyright: ignore[reportGeneralTypeIssues]

        assert run.contains_page_break == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "expected"),
        [
            # -- no content produces an empty iterator --
            ("w:r", []),
            # -- contiguous text content is condensed into a single str --
            ('w:r/(w:t"foo",w:cr,w:t"bar")', ["str"]),
            # -- page-breaks are a form of inner-content --
            (
                'w:r/(w:t"abc",w:br,w:lastRenderedPageBreak,w:noBreakHyphen,w:t"def")',
                ["str", "RenderedPageBreak", "str"],
            ),
            # -- as are drawings --
            (
                'w:r/(w:t"abc", w:lastRenderedPageBreak, w:drawing)',
                ["str", "RenderedPageBreak", "Drawing"],
            ),
        ],
    )
    def it_can_iterate_its_inner_content_items(
        self, r_cxml: str, expected: List[str], fake_parent: t.ProvidesStoryPart
    ):
        r = cast(CT_R, element(r_cxml))
        run = Run(r, fake_parent)

        inner_content = run.iter_inner_content()

        actual = [type(item).__name__ for item in inner_content]
        assert actual == expected, f"expected: {expected}, got: {actual}"

    def it_knows_its_character_style(self, style_get_fixture):
        run, style_id_, style_ = style_get_fixture
        style = run.style
        run.part.get_style.assert_called_once_with(style_id_, WD_STYLE_TYPE.CHARACTER)
        assert style is style_

    def it_can_change_its_character_style(self, style_set_fixture):
        run, value, expected_xml = style_set_fixture
        run.style = value
        run.part.get_style_id.assert_called_once_with(value, WD_STYLE_TYPE.CHARACTER)
        assert run._r.xml == expected_xml

    def it_knows_its_underline_type(self, underline_get_fixture):
        run, expected_value = underline_get_fixture
        assert run.underline is expected_value

    def it_can_change_its_underline_type(self, underline_set_fixture):
        run, underline, expected_xml = underline_set_fixture
        run.underline = underline
        assert run._r.xml == expected_xml

    @pytest.mark.parametrize("invalid_value", ["foobar", 42, "single"])
    def it_raises_on_assign_invalid_underline_value(self, invalid_value: Any):
        r = cast(CT_R, element("w:r/w:rPr"))
        run = Run(r, None)
        with pytest.raises(ValueError, match=" is not a valid WD_UNDERLINE"):
            run.underline = invalid_value

    def it_provides_access_to_its_font(self, font_fixture):
        run, Font_, font_ = font_fixture
        font = run.font
        Font_.assert_called_once_with(run._element)
        assert font is font_

    def it_can_add_text(self, add_text_fixture, Text_):
        r, text_str, expected_xml = add_text_fixture
        run = Run(r, None)

        _text = run.add_text(text_str)

        assert run._r.xml == expected_xml
        assert _text is Text_.return_value

    @pytest.mark.parametrize(
        ("break_type", "expected_cxml"),
        [
            (WD_BREAK.LINE, "w:r/w:br"),
            (WD_BREAK.PAGE, "w:r/w:br{w:type=page}"),
            (WD_BREAK.COLUMN, "w:r/w:br{w:type=column}"),
            (WD_BREAK.LINE_CLEAR_LEFT, "w:r/w:br{w:clear=left}"),
            (WD_BREAK.LINE_CLEAR_RIGHT, "w:r/w:br{w:clear=right}"),
            (WD_BREAK.LINE_CLEAR_ALL, "w:r/w:br{w:clear=all}"),
        ],
    )
    def it_can_add_a_break(self, break_type: WD_BREAK, expected_cxml: str):
        r = cast(CT_R, element("w:r"))
        run = Run(r, None)  # pyright:ignore[reportGeneralTypeIssues]
        expected_xml = xml(expected_cxml)

        run.add_break(break_type)

        assert run._r.xml == expected_xml

    def it_can_add_a_tab(self, add_tab_fixture):
        run, expected_xml = add_tab_fixture
        run.add_tab()
        assert run._r.xml == expected_xml

    def it_can_add_a_picture(self, add_picture_fixture):
        run, image, width, height, inline = add_picture_fixture[:5]
        expected_xml, InlineShape_, picture_ = add_picture_fixture[5:]

        picture = run.add_picture(image, width, height)

        run.part.new_pic_inline.assert_called_once_with(image, width, height)
        assert run._r.xml == expected_xml
        InlineShape_.assert_called_once_with(inline)
        assert picture is picture_

    @pytest.mark.parametrize(
        ("initial_r_cxml", "expected_cxml"),
        [
            ("w:r", "w:r"),
            ('w:r/w:t"foo"', "w:r"),
            ("w:r/w:br", "w:r"),
            ("w:r/w:rPr", "w:r/w:rPr"),
            ('w:r/(w:rPr, w:t"foo")', "w:r/w:rPr"),
            (
                'w:r/(w:rPr/(w:b, w:i), w:t"foo", w:cr, w:t"bar")',
                "w:r/w:rPr/(w:b, w:i)",
            ),
        ],
    )
    def it_can_remove_its_content_but_keep_formatting(
        self, initial_r_cxml: str, expected_cxml: str
    ):
        r = cast(CT_R, element(initial_r_cxml))
        run = Run(r, None)  # pyright: ignore[reportGeneralTypeIssues]
        expected_xml = xml(expected_cxml)

        cleared_run = run.clear()

        assert run._r.xml == expected_xml
        assert cleared_run is run

    @pytest.mark.parametrize(
        ("r_cxml", "expected_text"),
        [
            ("w:r", ""),
            ('w:r/w:t"foobar"', "foobar"),
            ('w:r/(w:t"abc", w:tab, w:t"def", w:cr)', "abc\tdef\n"),
            ('w:r/(w:br{w:type=page}, w:t"abc", w:t"def", w:tab)', "abcdef\t"),
        ],
    )
    def it_knows_the_text_it_contains(self, r_cxml: str, expected_text: str):
        r = cast(CT_R, element(r_cxml))
        run = Run(r, None)  # pyright: ignore[reportGeneralTypeIssues]
        assert run.text == expected_text

    def it_can_replace_the_text_it_contains(self, text_set_fixture):
        run, text, expected_xml = text_set_fixture
        run.text = text
        assert run._r.xml == expected_xml

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def add_picture_fixture(self, part_prop_, document_part_, InlineShape_, picture_):
        run = Run(element("w:r/wp:x"), None)
        image = "foobar.png"
        width, height, inline = 1111, 2222, element("wp:inline{id=42}")
        expected_xml = xml("w:r/(wp:x,w:drawing/wp:inline{id=42})")
        document_part_.new_pic_inline.return_value = inline
        InlineShape_.return_value = picture_
        return (run, image, width, height, inline, expected_xml, InlineShape_, picture_)

    @pytest.fixture(
        params=[
            ('w:r/w:t"foo"', 'w:r/(w:t"foo", w:tab)'),
        ]
    )
    def add_tab_fixture(self, request):
        r_cxml, expected_cxml = request.param
        run = Run(element(r_cxml), None)
        expected_xml = xml(expected_cxml)
        return run, expected_xml

    @pytest.fixture(
        params=[
            ("w:r", "foo", 'w:r/w:t"foo"'),
            ('w:r/w:t"foo"', "bar", 'w:r/(w:t"foo", w:t"bar")'),
            ("w:r", "fo ", 'w:r/w:t{xml:space=preserve}"fo "'),
            ("w:r", "f o", 'w:r/w:t"f o"'),
        ]
    )
    def add_text_fixture(self, request):
        r_cxml, text, expected_cxml = request.param
        r = element(r_cxml)
        expected_xml = xml(expected_cxml)
        return r, text, expected_xml

    @pytest.fixture(
        params=[
            ("w:r/w:rPr", "bold", None),
            ("w:r/w:rPr/w:b", "bold", True),
            ("w:r/w:rPr/w:b{w:val=on}", "bold", True),
            ("w:r/w:rPr/w:b{w:val=off}", "bold", False),
            ("w:r/w:rPr/w:b{w:val=1}", "bold", True),
            ("w:r/w:rPr/w:i{w:val=0}", "italic", False),
        ]
    )
    def bool_prop_get_fixture(self, request):
        r_cxml, bool_prop_name, expected_value = request.param
        run = Run(element(r_cxml), None)
        return run, bool_prop_name, expected_value

    @pytest.fixture(
        params=[
            # nothing to True, False, and None ---------------------------
            ("w:r", "bold", True, "w:r/w:rPr/w:b"),
            ("w:r", "bold", False, "w:r/w:rPr/w:b{w:val=0}"),
            ("w:r", "italic", None, "w:r/w:rPr"),
            # default to True, False, and None ---------------------------
            ("w:r/w:rPr/w:b", "bold", True, "w:r/w:rPr/w:b"),
            ("w:r/w:rPr/w:b", "bold", False, "w:r/w:rPr/w:b{w:val=0}"),
            ("w:r/w:rPr/w:i", "italic", None, "w:r/w:rPr"),
            # True to True, False, and None ------------------------------
            ("w:r/w:rPr/w:b{w:val=on}", "bold", True, "w:r/w:rPr/w:b"),
            ("w:r/w:rPr/w:b{w:val=1}", "bold", False, "w:r/w:rPr/w:b{w:val=0}"),
            ("w:r/w:rPr/w:b{w:val=1}", "bold", None, "w:r/w:rPr"),
            # False to True, False, and None -----------------------------
            ("w:r/w:rPr/w:i{w:val=false}", "italic", True, "w:r/w:rPr/w:i"),
            ("w:r/w:rPr/w:i{w:val=0}", "italic", False, "w:r/w:rPr/w:i{w:val=0}"),
            ("w:r/w:rPr/w:i{w:val=off}", "italic", None, "w:r/w:rPr"),
        ]
    )
    def bool_prop_set_fixture(self, request):
        initial_r_cxml, bool_prop_name, value, expected_cxml = request.param
        run = Run(element(initial_r_cxml), None)
        expected_xml = xml(expected_cxml)
        return run, bool_prop_name, value, expected_xml

    @pytest.fixture
    def font_fixture(self, Font_, font_):
        run = Run(element("w:r"), None)
        return run, Font_, font_

    @pytest.fixture
    def style_get_fixture(self, part_prop_):
        style_id = "Barfoo"
        r_cxml = "w:r/w:rPr/w:rStyle{w:val=%s}" % style_id
        run = Run(element(r_cxml), None)
        style_ = part_prop_.return_value.get_style.return_value
        return run, style_id, style_

    @pytest.fixture(
        params=[
            ("w:r", "Foo Font", "FooFont", "w:r/w:rPr/w:rStyle{w:val=FooFont}"),
            ("w:r/w:rPr", "Foo Font", "FooFont", "w:r/w:rPr/w:rStyle{w:val=FooFont}"),
            (
                "w:r/w:rPr/w:rStyle{w:val=FooFont}",
                "Bar Font",
                "BarFont",
                "w:r/w:rPr/w:rStyle{w:val=BarFont}",
            ),
            ("w:r/w:rPr/w:rStyle{w:val=FooFont}", None, None, "w:r/w:rPr"),
            ("w:r", None, None, "w:r/w:rPr"),
        ]
    )
    def style_set_fixture(self, request, part_prop_):
        r_cxml, value, style_id, expected_cxml = request.param
        run = Run(element(r_cxml), None)
        part_prop_.return_value.get_style_id.return_value = style_id
        expected_xml = xml(expected_cxml)
        return run, value, expected_xml

    @pytest.fixture(
        params=[
            ("abc  def", 'w:r/w:t"abc  def"'),
            ("abc\tdef", 'w:r/(w:t"abc", w:tab, w:t"def")'),
            ("abc\ndef", 'w:r/(w:t"abc", w:br,  w:t"def")'),
            ("abc\rdef", 'w:r/(w:t"abc", w:br,  w:t"def")'),
        ]
    )
    def text_set_fixture(self, request):
        new_text, expected_cxml = request.param
        initial_r_cxml = 'w:r/w:t"should get deleted"'
        run = Run(element(initial_r_cxml), None)
        expected_xml = xml(expected_cxml)
        return run, new_text, expected_xml

    @pytest.fixture(
        params=[
            ("w:r", None),
            ("w:r/w:rPr/w:u", None),
            ("w:r/w:rPr/w:u{w:val=single}", True),
            ("w:r/w:rPr/w:u{w:val=none}", False),
            ("w:r/w:rPr/w:u{w:val=double}", WD_UNDERLINE.DOUBLE),
            ("w:r/w:rPr/w:u{w:val=wave}", WD_UNDERLINE.WAVY),
        ]
    )
    def underline_get_fixture(self, request):
        r_cxml, expected_underline = request.param
        run = Run(element(r_cxml), None)
        return run, expected_underline

    @pytest.fixture(
        params=[
            ("w:r", True, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r", False, "w:r/w:rPr/w:u{w:val=none}"),
            ("w:r", None, "w:r/w:rPr"),
            ("w:r", WD_UNDERLINE.SINGLE, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r", WD_UNDERLINE.THICK, "w:r/w:rPr/w:u{w:val=thick}"),
            ("w:r/w:rPr/w:u{w:val=single}", True, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r/w:rPr/w:u{w:val=single}", False, "w:r/w:rPr/w:u{w:val=none}"),
            ("w:r/w:rPr/w:u{w:val=single}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:u{w:val=single}",
                WD_UNDERLINE.SINGLE,
                "w:r/w:rPr/w:u{w:val=single}",
            ),
            (
                "w:r/w:rPr/w:u{w:val=single}",
                WD_UNDERLINE.DOTTED,
                "w:r/w:rPr/w:u{w:val=dotted}",
            ),
        ]
    )
    def underline_set_fixture(self, request):
        initial_r_cxml, new_underline, expected_cxml = request.param
        run = Run(element(initial_r_cxml), None)
        expected_xml = xml(expected_cxml)
        return run, new_underline, expected_xml

    # fixture components ---------------------------------------------

    @pytest.fixture
    def document_part_(self, request):
        return instance_mock(request, DocumentPart)

    @pytest.fixture
    def Font_(self, request, font_):
        return class_mock(request, "skelmis.docx.text.run.Font", return_value=font_)

    @pytest.fixture
    def font_(self, request):
        return instance_mock(request, Font)

    @pytest.fixture
    def InlineShape_(self, request):
        return class_mock(request, "skelmis.docx.text.run.InlineShape")

    @pytest.fixture
    def part_prop_(self, request, document_part_):
        return property_mock(request, Run, "part", return_value=document_part_)

    @pytest.fixture
    def picture_(self, request):
        return instance_mock(request, InlineShape)

    @pytest.fixture
    def Text_(self, request):
        return class_mock(request, "skelmis.docx.text.run._Text")
