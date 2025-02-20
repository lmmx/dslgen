# polars-demo-lark

Experiment to create a parser grammar for a library—specifically **Polars**—using **Lark** for the grammar and **Griffe** to introspect the Polars Python API.

## Motivation

I wanted to explore how to:

1. **Dynamically discover** which methods Polars exposes (e.g., `pl.DataFrame.filter`, `pl.DataFrame.select`) without manually listing them.  
2. **Construct a minimal DSL** that recognizes valid Polars usage, like chaining `pl.DataFrame(...)` with `.filter(...)`, `.select(...)`, or `.lazy()`.  
3. Ensure the parser **accepts** valid Polars snippets and **rejects** invalid ones.

This code is my first attempt at building a Lark grammar and my first time using Griffe directly too.

---

## How It Works

### 1. Building the Polars API Map

The file [`demo_polars_lark.py`](./src/dslgen/demo_polars_lark.py) starts with a function called `build_polars_api_map()`:
```python
def build_polars_api_map():
    polars_module = load(
        "polars",
        try_relative_path=False,
        allow_inspection=True,
        force_inspection=True,
    )

    interesting_classes = ["DataFrame", "LazyFrame", "Expr"]
    found_objects = {}
    ...
    # Identify classes & methods dynamically

    api_map = { ... }  # e.g. "DataFrame" -> {"filter": ..., "select": ...}
    return api_map
```

- Griffe loads the Polars Python module (with forced inspection), which lets me discover internal structures like `DataFrame` and `LazyFrame`.  
- I iterate over each discovered class’s methods, building a mapping from class name to its methods—essentially the DSL “vocabulary.”  

### 2. Generating the Lark Grammar

Once I have that mapping, the code calls `generate_lark_grammar(api_map)`, which returns a Lark grammar string. It:

- Creates tokens for `pl.DataFrame(...)`, `.filter(...)`, `.select(...)`, etc.  
- Defines chaining rules so something like:
  ```plaintext
  pl.DataFrame({"x": [1,2,3]}).filter(...).select(...)
  ```
  is recognized.

```python
def generate_lark_grammar(api_map):
    grammar_prelude = r"""
    ?start: polars_expression

    ?polars_expression: dataframe_expression
                      | lazyframe_expression

    DATAFRAME_CALL: "pl.DataFrame" "(" /[^)]*/ ")"
    LAZYFRAME_CALL: ".lazy" "(" ")"
    """
    ...
    # Insert tokens for known methods like .filter(...), .select(...)
    # Then define chaining rules
```

Because this is minimal and a proof of concept, I capture everything inside parentheses (`([^)]*)`) as a single chunk without parsing the expression details.

### 3. Checking Validity with Tests

Under [`tests/test_demo_polars_lark.py`](./tests/test_demo_polars_lark.py):

1. `test_valid_snippets` checks that typical usage like `pl.DataFrame({"x": [1,2,3]}).filter(x>1)` parses successfully.  
2. `test_invalid_snippets` checks if nonsense code (`unknown_method()`) or syntax errors are rejected.  
3. `test_api_map_sanity` confirms the Polars methods I expect (e.g., `filter`, `select`, `lazy`) are indeed discovered by Griffe.  
4. `test_generate_lark_grammar_structure` ensures we actually generated tokens like `FILTER:` and `SELECT:` in the grammar.

The result is a small MVP that proves Lark can parse Polars-like code, verifying method chains are recognized while ignoring details like the expression inside parentheses.

---

## Limitations & Known Issue

- One test (`pl.DataFrame({"x": [1,2,3]}).filter(pl.col("x") > 1)`) sometimes fails because the grammar or the lexer doesn’t automatically accept the `>` character. This is not a showstopper, it just shows that Lark is very precise about how punctuation is tokenized. For a deeper parse of Python expressions, I’d need a more robust sub-grammar or a “catch-all” token that swallows `>` as part of the argument string.  
- This is a proof of concept and my first time using Lark and Griffe, so it’s intentionally kept simple. It doesn’t parse every possible Polars expression in detail—it just ensures method chaining is recognized and that valid/invalid usage can be distinguished at a high level.

---

## Why Is This Useful?

- **Dynamically discover Polars**: Because Griffe introspects the actual Polars library, I don’t have to manually maintain a list of methods. If Polars adds `new_method()`, I can potentially pick it up automatically.  
- **Prototype DSL**: This grammar demonstrates how to **model** library usage as a DSL—accepting known method names, rejecting unknown ones, and validating chaining logic. It could be extended to do real code linting or code generation.  
- **Potential for LLM Training**: If I want to train or fine-tune a model on valid Polars usage, this grammar helps me validate or generate syntactically correct code. I can ensure I’m feeding the model realistic chains.  
- **MVP**: It’s the “minimum viable product” to prove that Lark + Griffe can automate a DSL for Polars. Even though it’s not comprehensive, it sets the groundwork for more advanced features (like parsing the expression inside `filter(...)` or supporting more Polars classes).

---

## Extending

- **Parse inside parentheses**: If I want to handle expressions like `pl.col("x") > 1`, I’d define a sub-grammar for Python expressions or switch to the “basic” lexer with a big catch-all token.  
- **Add more Polars classes**: Right now, I look for `DataFrame`, `LazyFrame`, and `Expr`. More advanced usage might include `Series`, `GroupBy`, etc.  
- **Integration with LLM**: If I build a code generator or a specialized LLM prompt, I can use this grammar to ensure code is valid or do structured fuzzing of Polars calls.

---

## Conclusion

This proves that you can:

1. **Introspect** Polars with Griffe,  
2. **Generate** a Lark grammar from discovered methods,  
3. **Parse** and **test** real usage snippets (like `pl.DataFrame(...).filter(...)`).  

It’s my first attempt at using Lark and Griffe directly, so it’s minimal and not fully robust. Nevertheless, it validates the idea that Polars usage can be treated like a DSL for code analysis or generation.  

Next Steps might include refining how parentheses content is parsed, adding more advanced rules, or hooking this grammar into an automated code generator or AI assistant that helps with Polars code.
