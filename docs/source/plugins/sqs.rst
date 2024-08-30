SQS Plugin
==========

``deployfish-sqs`` is a plugin that provides notification via AWS SQS for service updates.

Configure deployfish-sqs
--------------------------

First follow the instructions for installing and configuring deployfish, then
add this stanza to your ``~/.deployfish.yml`` file::

    plugin.sqs:
        enabled: true
        queue:
          - name: <your-sqs-queue-name>
            type: <your-sqs-message-type>
            profile: <your-aws-profile>

Queue is a list, so a message will be sent to each queue in the list. Profile can be omitted
if you want your default profile to be used.

NOTE: ``~/.deployfish.yml`` is the config file for deployfish itself.  This is different from
the ``deployfish.yml`` file that defines your services and tasks.

