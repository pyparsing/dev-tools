from pathlib import Path

import pyparsing as pp
ppc = pp.pyparsing_common

PRINT_HIERARCHY_YUML = False
PRINT_REFERENCES_YUML = True

pp_text = Path('pyparsing.py').read_bytes()
pp_text = pp_text.decode('utf-8', errors='ignore')

names = pp.__all__
# print(len(names))

(CLASS, DEF,) = map(pp.Keyword, """class def""".split())
LPAR, RPAR, COLON = map(pp.Suppress, "():")

ident = ppc.identifier
# source_line = pp.Empty() + pp.restOfLine() + pp.LineEnd()
# source_line.setName("source line").setDebug()

indent_stack = []
class_expr = (CLASS - ident('class_name')
                      + pp.Optional(LPAR + pp.delimitedList(ident)('base_classes') + RPAR)
                      + COLON)

class_expr.addParseAction(pp.matchOnlyAtCol(1))

class_expr.ignore(pp.pythonStyleComment)
any_style_quoted_string = (pp.QuotedString("'''", multiline=True)
                           | pp.QuotedString('"""', multiline=True)
                           | pp.quotedString)
class_expr.ignore(any_style_quoted_string)
method_expr = (DEF - ident('method_name') + pp.nestedExpr() + COLON)
method_expr.addParseAction(pp.matchOnlyAtCol(1))

assignment_expr = ident('var_name') + '=' + pp.restOfLine()
assignment_expr.addParseAction(pp.matchOnlyAtCol(1))

other_expr = pp.Word(pp.printables).addParseAction(pp.matchOnlyAtCol(1)) + pp.restOfLine()


class_hierarchy = {}

# get class inheritance hierarchy
for i, (class_def, s, e) in enumerate(class_expr.scanString(pp_text)):
    if class_def.class_name not in names:
        # print(class_def.class_name)
        names.append(class_def.class_name)

    class_hierarchy[class_def.class_name] = class_def.base_classes
    if PRINT_HIERARCHY_YUML:
        for base in class_def.base_classes:
            print("[{}]^-[{}]".format(base, class_def.class_name))


# identify top-level classes, methods, etc. and their scopes
top_level = class_expr | method_expr | assignment_expr | other_expr
top_level.ignore(pp.pythonStyleComment)
top_level.ignore(any_style_quoted_string)


scopes = {}
last_name = None

for i, (top_level_def, s, e) in enumerate(top_level.scanString(pp_text)):

    if 'class_name' in top_level_def:
        # print('[' + class_def.class_name + ']')
        if last_name is not None:
            scopes[last_name].append(s)
        scopes[top_level_def.class_name] = [s]
        last_name = top_level_def.class_name

    elif 'method_name' in top_level_def:
        if last_name is not None:
            scopes[last_name].append(s)
        scopes[top_level_def.method_name] = [s]
        last_name = top_level_def.method_name

    elif 'var_name' in top_level_def:
        if last_name is not None:
            scopes[last_name].append(s)
        last_name = None
        if top_level_def.var_name in pp.__all__:
            scopes[top_level_def.var_name] = [s, e]

if last_name is not None:
    scopes[last_name].append(len(pp_text))


if PRINT_REFERENCES_YUML:

    references = {name: set() for name in scopes}
    comment_stripper = (any_style_quoted_string | pp.pythonStyleComment).suppress()

    for name, (start, end) in scopes.items():
        source_body = pp_text[start:end]
        # strip comments and quoted strings from body
        source_body = comment_stripper.transformString(source_body)

        for defined_name in scopes:
            if defined_name == name:
                continue
            if pp.Keyword(defined_name).searchString(source_body):
                references[name].add(defined_name)

    for name, refs in references.items():
        print('[' + name + ']')
        for ref in refs:
            print("[{}]->[{}]".format(name, ref))

