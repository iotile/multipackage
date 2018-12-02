"""jinja based template rendering."""

import os
from jinja2 import Environment, PackageLoader

def _quote(obj):
    return '"' + obj + '"'


def render_template(template_name, info, out_path=None, adjust_newlines=True):
    """Render a template using the variables in info.

    You can optionally render to a file by passing out_path.  This assumes
    that you are rendering text files that will be saved with UTF-8 encoding.

    By default, it modifies the generated template to have platform-specific
    newlines.  If you want the template's output to be unmodified, pass
    adjust_newlines=False.

    Args:
        template_name (str): The name of the template to load.  This must
            be a file in config/templates inside this package
        out_path (str): An optional path of where to save the output
            file, otherwise it is just returned as a string.
        info (dict): A dictionary of variables passed into the template to
            perform substitutions.
        adjust_newlines (bool): Automatically convert the output to have
            platform specific newlines.  Default: True.

    Returns:
        string: The rendered template data.
    """

    env = Environment(loader=PackageLoader('multipackage', 'data/templates'),
                      trim_blocks=True, lstrip_blocks=True)

    env.filters['quote'] = _quote

    template = env.get_template(template_name)
    result = template.render(info)

    if adjust_newlines:
        result_lines = result.splitlines()
        result = os.linesep.join(result_lines)

    if out_path is not None:
        with open(out_path, 'wb') as outfile:
            outfile.write(result.encode('utf-8'))

    return result
