.. _api-reference-label:

API Reference
=============

.. toctree::
  :hidden:

{% for key, component in components|dictsort %}
{% for package in component.desired_packages %}
  api/{{ package }} 
{% endfor %}
{% endfor %}
