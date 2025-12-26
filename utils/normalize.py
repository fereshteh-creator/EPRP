# Normalization utilities (strip comments, whitespace, etc.)
import ast, io, tokenize, textwrap

def _strip_comments(code: str) -> str:
    """Remove comments while preserving code layout."""
    sio = io.StringIO(code)
    out = []
    prev_end = (1, 0)
    try:
        for tok in tokenize.generate_tokens(sio.readline):
            ttype, tstr, start, end, line = tok
            if ttype == tokenize.COMMENT:
                continue
            # Fill any gaps with whitespace/newlines to keep positions stable
            (srow, scol), (erow, ecol) = start, end
            if prev_end[0] < srow:
                out.append("\n" * (srow - prev_end[0]))
                prev_end = (srow, 0)
            if prev_end[1] < scol:
                out.append(" " * (scol - prev_end[1]))
            out.append(tstr)
            prev_end = (erow, ecol)
    except Exception:
        # Be robust to malformed/partial code (IndentationError, TokenError, etc.).
        # Fall back to raw code if tokenization fails
        return code
    return "".join(out)

class _DocstringStripper(ast.NodeTransformer):
    """Remove module, class and function docstrings."""
    def _strip_first_expr_str(self, body):
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            return body[1:]
        return body

    def visit_Module(self, node):
        self.generic_visit(node)
        node.body = self._strip_first_expr_str(node.body)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        node.body = self._strip_first_expr_str(node.body)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        node.body = self._strip_first_expr_str(node.body)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        node.body = self._strip_first_expr_str(node.body)
        return node

def _strip_docstrings(code: str) -> str:
    try:
        tree = ast.parse(code)
        tree = _DocstringStripper().visit(tree)
        ast.fix_missing_locations(tree)
        # Python 3.9+: ast.unparse exists; else fallback to original code
        return ast.unparse(tree) if hasattr(ast, "unparse") else code
    except Exception:
        return code

def normalize_code_py(code: str) -> str:
    """Normalization used for matching: remove comments & docstrings, trim, collapse blank lines."""
    code_no_comments = _strip_comments(code)
    code_no_docs = _strip_docstrings(code_no_comments)
    # Dedent and collapse excessive blank lines:
    ded = textwrap.dedent(code_no_docs).strip()
    lines = [ln.rstrip() for ln in ded.splitlines()]
    # remove consecutive empty lines
    cleaned = []
    for ln in lines:
        if ln == "" and (cleaned and cleaned[-1] == ""):
            continue
        cleaned.append(ln)
    return "\n".join(cleaned)


def normalize_code_generic(code: str) -> str:
    """
    Lightweight normalization for non-Python languages:
    strip trailing whitespace, collapse blank lines, and trim.
    """
    lines = [ln.rstrip() for ln in textwrap.dedent(code).splitlines()]
    cleaned = []
    for ln in lines:
        if not ln and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


def normalize_code(code: str, language: str = "python") -> str:
    """
    Dispatch to the appropriate normalizer based on language label.
    Defaults to Python behavior.
    """
    if not language:
        language = "python"
    if language.lower().startswith("py"):
        return normalize_code_py(code)
    return normalize_code_generic(code)
