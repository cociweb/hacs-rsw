# hacs-rsw
Custom rest-switch

```
switch:
  - platform: rsw
    name: "My Switch"
    resource: http://ip_address/endpoint
    method: "post"
    body_on: '{"key": "value"}'
    body_off: '{"key": "value"}'
    value_template: >-
      {% if value_json.is_on == 'true' %}
      true
      {% else %}
      false
      {% endif %}
    headers:
      Content-Type: "application/json"
    timeout: 10
    unique_id: "my_switch"
    verify_ssl: True
    scan_interval: 30
```
