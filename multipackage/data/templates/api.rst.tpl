.. _api-reference-label:

API Reference
=============

.. toctree::
  :hidden:

{% for key, component in components|dictsort %}
{% for package in desired_packages[key] %}
  api/{{ package }} 
{% endfor %}
{% endfor %}
