.. _api-reference-label:

API Reference
=============

.. toctree::
  :hidden:

{% for key, component in components|dictsort %}
{% for package in component.packages %}
  api/{{ package }} 
{% endfor %}
{% endfor %}
