REPOSITORY: {{ repo.name }}

REQUIRED AND OPTIONAL ENVIRONMENT VARIABLES:
{% for name, declarations, value in repo.iter_secrets() %}
  - {{ name}}: {{ value | variable_status(declarations) }}
{% for declaration in declarations %}
    + Used by: {{ declaration.subsystem }}{% if not declaration.required %}, OPTIONAL{% endif %}

      {{ declaration.usage }}

{% endfor -%}
{% endfor %}
