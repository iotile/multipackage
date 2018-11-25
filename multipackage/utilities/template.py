"""jinja based template rendering."""

from jinja2 import Environment, PackageLoader


def render_template(template_name, info, out_path=None):
    """Render a template using the variables in info.

    You can optionally render to a file by passing out_path.

    Args:
        template_name (str): The name of the template to load.  This must
            be a file in config/templates inside this package
        out_path (str): An optional path of where to save the output
            file, otherwise it is just returned as a string.
        info (dict): A dictionary of variables passed into the template to
            perform substitutions.

    Returns:
        string: The rendered template data.
    """

    env = Environment(loader=PackageLoader('multipackage', 'data/templates'),
                      trim_blocks=True, lstrip_blocks=True)

    template = env.get_template(template_name)
    result = template.render(info)

    if out_path is not None:
        with open(out_path, 'wb') as outfile:
            outfile.write(result.encode('utf-8'))

    return result
