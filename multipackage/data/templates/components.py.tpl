COMPONENTS = {
{% for key, component in components|dictsort %}
    "{{ key }}": {"name": "{{ key }}", "path": "{{ component.relative_path }}", "options": {
{%- for name, value in component.options | dictsort %}
{{ name | quote }}: {{ value | quote }}{% if not loop.last %}, {% endif %}
{% endfor -%}
}}{% if not loop.last %},{% endif %}

{% endfor %}
}
