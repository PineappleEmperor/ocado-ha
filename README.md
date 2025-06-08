[![release][release-badge]][release-url]
[![commits-since-latest][commits-badge]][commits-url]
![stars][stars-badge]
![Dynamic Regex Badge][hacs-badge]
\
![build][python-badge]
![build][hassfest-badge]
![build][hacs-valid-badge]

Ocado UK Integration for Home Assistant
=====================================

This is an unofficial Ocado integration for Home Assistant. This integration creates several sensors with information about your next delivery, and when you can edit your next delivery.

I'd suggest creating a new email address and set up auto-forwarding on any emails you wish this integration, or any other IMAP integration to access.

:warning: Please note this integration is in early development, there may be some rough edges and errors, so please submit any issues you come across!

Installation
------------

### HACS (Home Assistant Community Store)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pineappleemperor&repository=ocado-ha&category=Integration)


Configuration
-------------

### Adding the Integration

1.  In Home Assistant, navigate to **Configuration** > **Devices & Services**.
2.  Click on **Add Integration** and search for "Ocado".
3.  Fill in the required fields similar to most IMAP-based integrations.

### Configuration Options

You can configure the integration options by navigating to **Configuration** > **Devices & Services**, selecting the Ocado integration, and clicking on **Options**. Currently this is limited to:

<div style="margin-left: 25px;">

| **Option**        | **Description**                                            |
|-------------------|------------------------------------------------------------|
| **Scan interval** | How often you want to scan for new emails, by default this is every 10m, but it'll accept anything above every 5m. |
| **IMAP days**     | This is how many days in the past to scan for - if you prebook deliveries over a month in advance you may wish to extend this beyond the default 31d. If you reduce it too low the integration may not function correctly since it will miss important emails. |

</div>

Features
--------
### Example Cards

[Custom Button Card](/docs/community_templates/custom_button_card.yaml) by @PineappleEmperor
\
<img src="/docs/images/custom_button_card.png" alt="Example Custom Button Card" width="500"/>

[Bubble Popup Card with Markdown](/docs/community_templates/bubble_card_markdown.yaml) by @PineappleEmperor
\
<img src="/docs/images/bubble_card_markdown.png" alt="Example Bubble Card Popup with Markdown (for BBDs)" width="500"/>

### Tips & Tricks

* I send a reminder to edit my next delivery via a notification an hour before the edit deadline. To do this I created a template sensor for the countdown and a datetime helper to store the current edit deadline:

<div style="margin-left: 25px;">
<details>
<summary><strong>Template Sensor</strong></summary>


```
- name: "Ocado Edit Countdown"
    unique_id: ocado_edit_countdown
    availability: "{{ states('sensor.ocado_next_edit_deadline') not in ['unknown', 'unavailable', 'None', None] }}"
    icon: mdi:calendar-alert
    state: >
    {% set edit_deadline = states('sensor.ocado_next_edit_deadline')|as_datetime %}
    {% set edit_reminder = edit_deadline + timedelta(hours=-1) %}
    {% set now_datetime = states('sensor.date_time_iso')|as_datetime %}
    {% if (now_datetime.date() != edit_reminder.date()) %}
        -1
    {% elif edit_reminder.time() > edit_deadline.time() %}
        -1
    {% else %}
        {{ edit_deadline|time_until(precision=1)|replace(' hours','h')|replace(' minutes','m') }}
    {% endif %}
```
</details>


<details>
<summary><strong>Automation</strong></summary>


```
alias: Notify - Ocado Reminders
description: "Automation to send a reminder there's not much time left to edit the next Ocado order."
triggers:
- trigger: time
    at:
    entity_id: input_datetime.ocado_edit_reminder
    offset: "-01:00:00"
    id: edit_reminder
conditions: []
actions:
- choose:
    - conditions:
        - condition: trigger
            id:
            - edit_reminder
        sequence:
        - data:
            title: Ocado
            message: >-
                There's {{ states("sensor.ocado_edit_countdown") }} left to edit
                the Ocado order!
            action: notify.phones
mode: single
```
</details>
</div>
<br>

I also have a grocery budget 'pot' and an extension to the notification can inform me if I need to top up the pot based on the estimated total.


### Devices & Sensors

The integration offers 2 devices. The first contains the details about upcoming orders:
<details>
<summary><strong>Ocado (UK) Deliveries</strong></summary>
This device has 5 sensors:
<div style="margin-left: 25px;">
<details>
<summary><strong>Last Total Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides the last total using the email that is usually delivered a short time after a delivery.

It has two attributes:

| **Attribute**     | **Description**                                            |
|-------------------|------------------------------------------------------------|
| **Updated**       | This is the datetime of the email the info was taken from. |
| **Order Number**  | The order number associated with the total.                |

</div>
</details>


<details>
<summary><strong>Next Delivery Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides the date of the next booked delivery using the collation of all "order is confirmed" emails available.

It has six attributes:

| **Attribute**          | **Description**                                            |
|------------------------|------------------------------------------------------------|
| **Updated**            | This is the datetime of the email the info was taken from. |
| **Order Number**       | The order number associated with the total.                |
| **Delivery datetime**  | This is the datetime found for the next delivery.          |
| **Delivery window**    | This is the delivery window found for the next delivery.   |
| **Edit deadline**      | This is the edit deadline found for the next delivery.     |
| **Estimated total**    | This is the estimated total found for the next delivery.   |

</div>
</details>


<details>
<summary><strong>Next Edit Deadline Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides the datetime of the next order's edit deadline using the last "order is confirmed" email.

It has two attributes:

| **Attribute**     | **Description**                                            |
|-------------------|------------------------------------------------------------|
| **Updated**       | This is the datetime of the email the info was taken from. |
| **Order Number**  | The order number associated with the total.                |

</div>
</details>


<details>
<summary><strong>Upcoming Delivery Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides the date of the next booked delivery after the next booked delivery using the collation of all "order is confirmed" emails available.

It has six attributes:

| **Attribute**          | **Description**                                                |
|------------------------|----------------------------------------------------------------|
| **Updated**            | This is the datetime of the email the info was taken from.     |
| **Order Number**       | The order number associated with the total.                    |
| **Delivery datetime**  | This is the datetime found for the upcoming delivery.          |
| **Delivery window**    | This is the delivery window found for the upcoming delivery.   |
| **Edit deadline**      | This is the edit deadline found for the upcoming delivery.     |
| **Estimated total**    | This is the estimated total found for the upcoming delivery.   |

</div>
</details>


<details>
<summary><strong>Orders Sensor (disabled by default)</strong></summary>
<div style="margin-left: 25px;">

This sensor provides a list (via its attribute) of all future orders that have been parsed by the integration. The state of the sensor is the datetime it was last updated.

It has a single attribute:

| **Attribute**     | **Description**                                                              |
|-------------------|------------------------------------------------------------------------------|
| **orders**        | This is the list of future orders that have been parsed by the integration.  |

</div>
</details>
</div>
</details>


<details>
<summary><strong>Ocado (UK) Deliveries</strong></summary>
<div style="margin-left: 25px;">
This device has a sensor for each day of the week:
<details>
<summary><strong>{{day}} Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides number of best before dates on the chosen day/date.

It has four attributes:

| **Attribute**     | **Description**                                            |
|-------------------|------------------------------------------------------------|
| **Updated**       | This is the datetime of the email the info was taken from. |
| **Order Number**  | The order number associated with the total.                |
| **Date**          | The date teh day falls on (i.e. the best before date).     |
| **BBDs**          | The list of items with a best before date on this date.    |

</div>
</details>
</div>
</details>

Future Plans
--------
1. Testing 😅
3. Other online grocery vendors? (in separate repos)

<!-- Badges -->

[commits-badge]: https://img.shields.io/github/commits-since/PineappleEmperor/ocado-ha/latest?style=flat-square
[downloads-badge]: https://img.shields.io/github/downloads/pineappleemperor/ocado-ha/total?style=flat-square
[hacs-badge]: https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2Fhacs%2Fdefault%2Frefs%2Fheads%2Fmaster%2Fintegration&search=(%22PineappleEmperor%2Focado-ha%22)&replace=default&style=flat-square&label=hacs&link=https%3A%2F%2Fgithub.com%2Fhacs%2Fintegration
[hacs-valid-badge]: https://img.shields.io/github/actions/workflow/status/PineappleEmperor/ocado-ha/hacs_validate.yml?style=flat-square&label=hacs%20valid
[hassfest-badge]: https://img.shields.io/github/actions/workflow/status/PineappleEmperor/ocado-ha/hassfest_validate.yml?style=flat-square&label=hassfest
[python-badge]: https://img.shields.io/github/actions/workflow/status/PineappleEmperor/ocado-ha/python_validate.yml?style=flat-square&label=python
[release-badge]: https://img.shields.io/github/v/release/PineappleEmperor/ocado-ha?style=flat-square
[stars-badge]: https://img.shields.io/github/stars/PineappleEmperor/ocado-ha?style=flat-square

<!-- References -->

[commits-url]: https://github.com/PineappleEmperor/ocado-ha/commits/main/
[hacs-url]: https://github.com/hacs/integration
[release-url]: https://github.com/PineappleEmperor/ocado-ha/releases
