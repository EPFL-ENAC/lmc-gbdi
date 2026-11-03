"""The glossary keys lmc-openbdf's meanings by the labels the app prints."""

from app.glossary import glossary


def test_a_material_class_reads_its_description():
    assert glossary().terms["4.2 Concrete"]


def test_a_stage_printed_short_reads_its_long_name():
    assert glossary().terms["A1-A3"] == "A1-A3 Product Stage"


def test_a_data_type_in_the_overview_words_reads_openbdf_meaning():
    assert (
        "Construction Products Regulation"
        in glossary().terms["Construction Products Regulation data"]
    )


def test_a_project_field_reads_its_description():
    assert glossary().fields["building_gross_floor_area"] == "Total gross floor area."


def test_a_label_that_adds_nothing_has_no_entry():
    # "2.1 Frame" has no description, and its display name is the label itself.
    assert "2.1 Frame" not in glossary().terms
