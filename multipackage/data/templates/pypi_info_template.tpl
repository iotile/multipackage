{% if repo.clean %}
STATUS: Repository is up-to-date with no problems.
{% elif repo.settings_changed %}
STATUS: Repository needs to be updated.

RUN TO UPDATE:
    multipackage update {{ repo.path | default("") }}
{% elif repo.clean %}
STATUS: Repository has {{ repo.warnings | length }} warning(s)
{% else %}
STATUS: Repository has {{ repo.errors | length }} error(s) that need to be addressed
{% endif %}

COMPONENTS:
{% for key, component in repo.components | dictsort %}
  - {{ component.name }}: {{component.relative_path}} 
    python-version={{ component.options.compatibility | default('universal')}}
    packages: {{ repo.template.desired_packages[key] | join(", ")}}
{% endfor %}

SUBSYSTEMS:
{% for subsystem in repo.subsystems %}
  - {{ subsystem.SHORT_NAME }}: {{ subsystem.status | default("ENABLED") }} 
    {{ subsystem.SHORT_DESCRIPTION | default("no description available") }}
{% endfor %}

{%- if repo.errors %}

ERRORS:
{% for error in repo.errors %}
  - {{ error[0] }}: {{ error[1] }}
    FIX: {{ error[2] }}

{% endfor %}
{% endif %}

{%- if repo.warnings %}

WARNINGS:
{% for warning in repo.warnings %}
  - {{ warning[0] }}: {{ warning[1] }}
    FIX: {{ warning[2] }}

{% endfor %}
{% endif -%}
