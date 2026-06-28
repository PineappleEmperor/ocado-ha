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

Use Cases
---------

The integration turns your Ocado order emails into entities you can automate against. Common things people do with it:

* **Edit-deadline reminders** — get a notification an hour before you can no longer amend your next order (see [Tips & Tricks](#tips--tricks)).
* **Delivery-day awareness** — show "your next delivery is in 2 days" on a dashboard, or trigger a "bring the shopping in" reminder when the delivery window starts.
* **Budgeting** — react to the estimated total of an upcoming order, or top up a grocery "pot" automatically.
* **Voucher tracking** — surface the most recent Ocado Price Promise voucher and its value before it expires.
* **Calendar overlays** — see deliveries and edit deadlines alongside the rest of your life in any Home Assistant calendar card.

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

The setup form asks for standard IMAP connection parameters:

<div style="margin-left: 25px;">

| **Parameter**             | **Description**                                          | **Default**       |
|---------------------------|---------------------------------------------------------|-------------------|
| **IMAP email**            | The mailbox to read Ocado emails from.                  | –                 |
| **Password**              | Password (or app password) for that mailbox. Stored in your Home Assistant configuration. | – |
| **IMAP server**           | IMAP host for the mailbox.                              | `imap.gmail.com`  |
| **IMAP server port**      | IMAP SSL port.                                          | `993`             |
| **Email account folder**  | Folder/label to scan for Ocado emails.                  | `INBOX`           |

</div>

If the password later stops working (e.g. you rotate it), Home Assistant raises a **re-authentication** prompt so you can enter the new password without removing the integration.

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

The integration offers a single device containing the details about your orders:
<details>
<summary><strong>Ocado (UK) Deliveries</strong></summary>
This device has 6 sensors:
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

This sensor provides a list (via its attribute) of all future orders that have been parsed by the integration. The state of the sensor is the number of future orders currently parsed; the orders themselves are exposed as structured dictionaries in the attribute.

It has a single attribute:

| **Attribute**     | **Description**                                                              |
|-------------------|------------------------------------------------------------------------------|
| **orders**        | This is the list of future orders that have been parsed by the integration.  |

</div>
</details>


<details>
<summary><strong>Latest Voucher Sensor</strong></summary>
<div style="margin-left: 25px;">

This sensor provides the amount of the most recent valid Ocado Price Promise voucher. The state is the voucher amount (GBP); it clears once the voucher's validity date has passed.

It has four attributes:

| **Attribute**     | **Description**                                            |
|-------------------|------------------------------------------------------------|
| **Updated**       | This is the datetime of the email the info was taken from. |
| **Voucher**       | The voucher code.                                          |
| **Amount**        | The voucher amount.                                        |
| **Valid until**   | The date the voucher is valid until.                       |

</div>
</details>
</details>

### Calendars

The integration also creates two calendar entities on the same device, so deliveries and edit deadlines show up in any calendar card or `calendar.*` automation:

<div style="margin-left: 25px;">

| **Calendar**        | **Entity**                          | **Events**                                                                 |
|---------------------|-------------------------------------|----------------------------------------------------------------------------|
| **Deliveries**      | `calendar.ocado_uk_deliveries`      | One all-window event per booked delivery, spanning the delivery slot.       |
| **Edit Deadlines**  | `calendar.ocado_uk_edit_deadlines`  | A short marker event at each order's amend-by time.                         |

</div>

The events are rebuilt from the parsed orders on every read, so a cancelled or moved order is reflected automatically — no stale events linger. The event title format for each calendar is configurable from the integration's **Options** (see [Configuration Options](#configuration-options)).

How Data Updates
----------------

This is a `cloud_polling` integration: it does not receive push updates. On each poll it connects to your mailbox over IMAP, reads the recent Ocado emails (confirmations, totals, vouchers) and rebuilds the sensor and calendar state from them.

* **Poll frequency** is the **Scan interval** option (default every 10 minutes, minimum every 5 minutes).
* **History window** is the **IMAP days** option (default 31 days) — how far back each poll looks for relevant emails.
* A poll that fails transiently (network blip, mail host down) keeps the last-known data rather than blanking the sensors; a delivery stays relevant for days. After several consecutive failures a **repair issue** is raised so a persistent problem is visible.

Because there is no Ocado API, every value comes from parsing the emails Ocado sends — so an entity only appears once the corresponding email has arrived and been polled.

Known Limitations
-----------------

* **No real-time updates.** Data is only as fresh as the last poll; expect up to your scan-interval of lag after an email arrives.
* **Email-format dependent.** Parsing relies on Ocado's current email layouts. If Ocado changes a template, a sensor may stop populating until the parser is updated — please open an issue with a (redacted) example.
* **UK Ocado only.** The parsers target Ocado UK emails; other Ocado-powered retailers are not supported.
* **English-language emails** are assumed for date and amount parsing.
* **Best-before-date sensors** are not yet available (parked pending an Ocado receipt-format change).
* **No write access.** The integration reads your mailbox; it cannot place, amend or cancel orders.

Troubleshooting
---------------

| **Symptom**                                  | **Likely cause / fix**                                                                                                                                  |
|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Setup fails / re-auth prompt appears**     | The mailbox credentials were rejected. Check the username/password (use an **app password** for Gmail and similar), then complete the re-auth prompt.   |
| **No sensors populate**                      | Confirm the **IMAP server**, **port** and **folder** are correct and that Ocado emails actually reach that folder/label. Increase **IMAP days** if your next order is booked far in advance. |
| **A sensor is `unknown` / missing**          | The relevant email hasn't been received/polled yet (e.g. no recent total, or no valid voucher). It will populate on the next poll after the email arrives. |
| **Data looks stale**                         | Reduce the **Scan interval**, but keep it at 5 minutes or above. A transient fetch error keeps the previous data on purpose.                            |
| **A repair issue about refresh failures**    | The mailbox has been unreachable for several consecutive polls. Check connectivity and credentials; the issue clears automatically once a poll succeeds. |
| **Orders sensor is absent**                  | It is **disabled by default** — enable it from the entity's settings if you want the full parsed-orders list.                                            |

For anything else, enable debug logging for the integration (**Settings → Devices & Services → Ocado → Enable debug logging**) and include the log when opening an issue. Diagnostics can also be downloaded from the device page; credentials are redacted.

Removal
-------
Navigate to **Settings** > **Devices & Services**, select the Ocado integration, open the three-dot menu and choose **Delete**. This removes the config entry, its device and all of its sensors. No changes to your mailbox or Ocado account are needed.

Development
-----------

> [!NOTE]
> **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/pineapple-claude-hacs) skill. Architecture and final review are mine; every change is human-reviewed before it merges.

Future Plans
--------
1. Best-before-date sensors (parked pending an Ocado receipt-format change)
2. Interfacing with the core IMAP integration for email retrieval, ideally with OAuth2 support

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
