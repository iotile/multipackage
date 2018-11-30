COMPONENTS = {
{% for key, component in components|dictsort %}
    "{{ key }}": {"name": "{{ key }}", "path": "{{ component.relative_path }}", "compat": "{{ component.compatibility }}", "packages": [{% for package in component.toplevel_packages|sort %}"{{ package }}"{% if not loop.last %},{% endif %}{% endfor %}]}{% if not loop.last %},{% endif %}
{% endfor %}

}
