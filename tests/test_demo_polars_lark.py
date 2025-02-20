# tests/test_demo_polars_lark.py
import pytest
from dslgen import build_polars_api_map, generate_lark_grammar
from lark import Lark, UnexpectedInput


@pytest.fixture(scope="module")
def polars_parser():
    """
    Fixture that returns a Lark parser generated from the Polars API map.
    We do this once per test session for efficiency.
    """
    api_map = build_polars_api_map()
    grammar = generate_lark_grammar(api_map)
    parser = Lark(grammar, parser="lalr")
    return parser


def test_grammar_generation(polars_parser):
    """
    Basic check that the parser can be constructed and grammar is not empty.
    """
    # If parser instantiation failed, the fixture would raise an exception.
    # We can also check the grammar is non-empty:
    assert polars_parser.rules, "No rules generated in the grammar"


@pytest.mark.parametrize(
    "snippet",
    [
        # Simple DataFrame usage with no method chain
        'pl.DataFrame({"x": [1,2,3]})',
        # Chaining a known DataFrame method
        'pl.DataFrame({"x": [1,2,3]}).filter(pl.col("x") > 1)',
        # Chaining multiple DataFrame methods (assuming they're recognized)
        'pl.DataFrame({"x": [1,2,3]}).filter(x > 1).select("x")',
        # Transition to LazyFrame (if your grammar includes that):
        'pl.DataFrame({"x": [1,2,3]}).lazy().filter(x > 1).select("x")',
    ],
)
def test_valid_snippets(polars_parser, snippet):
    """
    Ensure valid Polars DSL-like snippets parse successfully under our grammar.
    """
    # We expect these to parse without error.
    parse_tree = polars_parser.parse(snippet)
    assert parse_tree, f"Failed to parse a valid snippet: {snippet}"


@pytest.mark.parametrize(
    "snippet",
    [
        # Unknown method
        'pl.DataFrame({"x": [1,2,3]}).unknown_method()',
        # Missing parentheses
        'pl.DataFrame{"x": [1,2,3]}',  # invalid syntax
        # Possibly a method from LazyFrame used directly on DataFrame if
        # we didn't define that in the grammar
        'pl.DataFrame({"x": [1,2,3]}).collect()',
    ],
)
def test_invalid_snippets(polars_parser, snippet):
    """
    Ensure invalid snippets (unknown methods, syntax errors) do NOT parse
    and raise an appropriate exception.
    """
    with pytest.raises(UnexpectedInput):
        polars_parser.parse(snippet)


def test_api_map_sanity():
    """
    Simple check that build_polars_api_map finds some known Polars classes/methods.
    """
    api_map = build_polars_api_map()
    assert "DataFrame" in api_map, "DataFrame not found in Polars API map"
    assert "LazyFrame" in api_map, "LazyFrame not found in Polars API map"

    df_methods = api_map["DataFrame"]
    # Check that we at least discovered some methods, e.g., "filter" or "select"
    known_methods = {"filter", "select", "lazy"}
    intersection = known_methods.intersection(df_methods.keys())
    assert intersection, "Expected at least one known DataFrame method in the API map"


def test_generate_lark_grammar_structure():
    """
    Check that our generated grammar contains essential tokens or rules
    for recognized methods.
    """
    api_map = build_polars_api_map()
    grammar_text = generate_lark_grammar(api_map)

    # For instance, ensure 'FILTER:' or 'SELECT:' tokens appear if we recognized them
    assert "FILTER:" in grammar_text, "FILTER token not found in generated grammar"
    assert "SELECT:" in grammar_text, "SELECT token not found in generated grammar"
