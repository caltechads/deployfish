Slack Plugin
============

``deployfish-slack`` is a plugin that provides notification via slack for service updates.

Configure deployfish-slack
--------------------------

First follow the instructions for installing and configuring deployfish, then
add this stanza to your ``~/.deployfish.yml`` file::

    plugin.slack:
        enabled: true
        token: <your-slack-token>
        channel: <your-slack-channel>

If you specify a channel of ``<user>``, the slack message will be sent to the user who
initiated the deploy.

NOTE: ``~/.deployfish.yml`` is the config file for deployfish itself.  This is different from
the ``deployfish.yml`` file that defines your services and tasks.

