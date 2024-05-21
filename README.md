# **Custom Rest Switch**

The `rsw` platform enhances Home Assistant by enabling users to create switches that interact with RESTful APIs or endpoints. The key functional difference lies in its flexibility compared to the official restful switch. Unlike the standard switch, the custom rest-switch allows more granular control over defining endpoints and handling responses. Users can tailor behavior based on specific API outcomes. Additionally, this custom component addresses a bug in the official rest-switch: the `is_on_template` feature is only available if `state_resource` is defined. However, in the custom rest-switch, you can use any available entity state or template, provided it corresponds to on/off, true/false, or 1/0 states.


## Installation
### Manual installation
1) Download the component
2) Place the folder custom_components/rsw into the config/custom_components/ path of your home assistant installation
3) Restart Home Assistant
4) add configuration to your `configuration.yaml`

### HACS Installation
1) Open HACS Dashboard and add the following repository at custom repository submenu in the 3-dotted menu on top right corner: [https://github.com/cociweb/hacs-rsw](https://github.com/cociweb/hacs-rsw)
2) Search and Download Custom Rest Switch component with HACS
4) Restart Home Assistant
5) add configuration to your `configuration.yaml`

## Configuration
To add Custom Rest Switch integration to your installation, add the following to your `configuration.yaml` file:

```
switch:
  - platform: rsw
    name: "My Switch"
    resource: http://ip_address/endpoint
    method: "post"
    body_on: '{"key": "value"}'
    body_off: '{"key": "value"}'
    value_template: >-
      {% if states('sensor.entity') | int  > 100 %}
      true
      {% else %}
      false
      {% endif %}
    headers:
      Content-Type: "application/json"
    timeout: 10
    unique_id: "switch.my_switch"
    verify_ssl: False
    scan_interval: 30
```
