#!/usr/bin/env python
"""demo_polars_lark.py

Proof-of-concept script:
1. Uses Griffe to load Polars' Python API (via force_inspection).
2. Builds a toy Lark grammar reflecting a tiny subset of Polars usage.
3. Demonstrates parsing a short Polars-like snippet.
"""

import sys

# --- 1. Griffe for introspection (public API) ---
from griffe import ExprAttribute, ExprName, load

# --- 2. Lark for grammar & parsing ---
from lark import Lark


def find_object_by_name(module, target_name):
    """Recursively search `module.members` for an object named `target_name`,
    returning the first match. If not found, return None.
    """
    if module.name.endswith(target_name):
        return module

    for member in module.members.values():
        if member.name.endswith(target_name):
            return member

    for member in module.members.values():
        found = find_object_by_name(member, target_name)
        if found is not None:
            return found

    return None


def _flatten_expr_attribute(expr_attr: ExprAttribute) -> list[str]:
    """Recursively extract a list of name segments from an ExprAttribute.
    E.g., ExprAttribute(values=[ExprName('pd'), ExprName('DataFrame')])
    -> ['pd', 'DataFrame']
    """
    parts = []
    for val in expr_attr.values:
        if isinstance(val, ExprName):
            parts.append(val.name)
        elif isinstance(val, ExprAttribute):
            # Recursively flatten
            parts.extend(_flatten_expr_attribute(val))
        else:
            # Fallback if it’s some other node
            parts.append(str(val))
    return parts


def build_polars_api_map():
    """Use Griffe to load Polars' public API with forced inspection,
    gather references to classes like DataFrame, LazyFrame, Expr,
    and map out the relevant methods + returns.

    Returns a dict like: {
       "DataFrame": { method_name -> return_type or None },
       "LazyFrame": { method_name -> return_type or None },
       "Expr":      { ... },
       ...
    }
    """
    polars_module = load(
        "polars",
        try_relative_path=False,
        allow_inspection=True,
        force_inspection=True,
    )

    interesting_classes = ["DataFrame", "LazyFrame", "Expr"]
    found_objects = {}
    for cls_name in interesting_classes:
        obj = find_object_by_name(polars_module, cls_name)
        if obj is not None:
            found_objects[cls_name] = obj

    api_map = {}
    for cls_name, cls_obj in found_objects.items():
        methods_dict = {}
        for subname, subobj in cls_obj.members.items():
            if subobj.is_function:
                ann = subobj.returns
                returns = None

                if ann is not None:
                    if isinstance(ann, ExprName):
                        # E.g. ExprName(name='DataFrame')
                        returns = ann.name
                    elif isinstance(ann, ExprAttribute):
                        # e.g. ExprAttribute(values=[ExprName('pd'), ExprName('DataFrame')])
                        chain = _flatten_expr_attribute(ann)
                        returns = ".".join(chain)
                    else:
                        # Fallback if it's some other node type (ExprSubscript, etc.)
                        # If you want to handle them more precisely, add more branches
                        returns = str(ann)

                methods_dict[subname] = returns

        api_map[cls_name] = methods_dict

    return api_map


def generate_lark_grammar(api_map):
    """Generate a simplistic Lark grammar for Polars usage.
    We'll define a 'start' rule to parse something like:

        pl.DataFrame({"x": [1,2,3]}).lazy().filter(...).select(...)

    This is a big oversimplification, but illustrates the approach.
    """
    grammar_prelude = r"""
    ?start: polars_expression

    // Let's define a rule that can represent either a DataFrame chain or a LazyFrame chain.
    ?polars_expression: dataframe_expression
                      | lazyframe_expression

    // For this demo, let's treat "df = pl.DataFrame(...)" as a single token, ignoring arguments.
    DATAFRAME_CALL: "pl.DataFrame" "(" /[^)]*/ ")"

    // We'll do the same for "df.lazy()" calls, ignoring what's inside.
    LAZYFRAME_CALL: ".lazy" "(" ")"
    """

    df_methods = api_map.get("DataFrame", {})
    lf_methods = api_map.get("LazyFrame", {})

    known_df_methods = ["select", "filter", "groupby", "join", "lazy"]
    known_lf_methods = ["collect", "filter", "select", "groupby"]

    dataframe_methods = [m for m in df_methods if m in known_df_methods]
    lazyframe_methods = [m for m in lf_methods if m in known_lf_methods]

    method_rules = []
    for method in set(dataframe_methods + lazyframe_methods):
        uppercase_name = method.upper()
        rule = f'{uppercase_name}: ".{method}" "(" /[^)]*/ ")"'
        method_rules.append(rule)

    grammar_mid = r"""
    ?dataframe_expression: DATAFRAME_CALL dataframe_chain?
    ?lazyframe_expression: DATAFRAME_CALL LAZYFRAME_CALL lazyframe_chain?

    dataframe_chain: (DF_METHOD_CALL)+
    lazyframe_chain: (LF_METHOD_CALL)+
    """

    df_method_call_tokens = [m.upper() for m in dataframe_methods]
    lf_method_call_tokens = [m.upper() for m in lazyframe_methods]

    df_call_rule = (
        f"DF_METHOD_CALL: {' | '.join(df_method_call_tokens)}"
        if df_method_call_tokens
        else "DF_METHOD_CALL: /NO_DF_METHODS/"
    )
    lf_call_rule = (
        f"LF_METHOD_CALL: {' | '.join(lf_method_call_tokens)}"
        if lf_method_call_tokens
        else "LF_METHOD_CALL: /NO_LF_METHODS/"
    )

    grammar = "\n".join(
        [
            grammar_prelude,
            "\n".join(method_rules),
            grammar_mid,
            df_call_rule,
            lf_call_rule,
        ]
    )

    return grammar


def main():
    # 1. Build an API map from Polars using Griffe
    api_map = build_polars_api_map()

    # 2. Generate a toy Lark grammar
    lark_grammar = generate_lark_grammar(api_map)

    print("===== GENERATED LARK GRAMMAR =====")
    print(lark_grammar)
    print("==================================")

    # 3. Construct the Lark parser
    parser = Lark(lark_grammar, parser="lalr")

    # 4. Test parsing a snippet
    test_snippet = r'pl.DataFrame({"x":[1,2,3]}).filter(x>1).select(["x"])'
    print("===== PARSING TEST SNIPPET =====")
    print(test_snippet)
    parsed_tree = parser.parse(test_snippet)
    print("===== PARSED LARK TREE =====")
    print(parsed_tree.pretty())


if __name__ == "__main__":
    sys.exit(main())
