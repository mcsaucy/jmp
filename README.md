# JMP -- URL shortener #

A URL shortener for the rest of us.

## Features ##
+ simple config file
+ robust, underlying API
+ swappable frontend
+ 

## Workflow ##
+ user creates a JMP link
    - user link quotas enforced to prevent abuse
+ user shares JMP link
    - links are NOT protected by any authentication
+ other users navigate to said JMP link which will then 301 to the target
    - track click frequency, IP, user agents


## NOTES ##
### Possible tables needed: ###
    - links table
        + link ID -- primary, autoinc
        + short link
        + full link
        + owner ID
    - owner table
        + owner ID -- primary, autoinc
        + owner entry UUID
        + count of existing links (for quota purposes)

### TODO: ###
    - add config file reader (also, define config schema; something simple)
        + consider OLC
    - detach database logic to allow for SQL database plugins
        + create sqlite plugin
    - auto-create database tables if they don't exist
        + have this functionality rolled into DB plugins
    - require webauth login
        + consider defining authentication plugins

### Options to prevent abuse: --> because someone _will_ abuse this ###
    - link quota
        + someone will use it a lot and get pissed
        + could result in lots of dead links when people clean up
        + quota management is another feature I would need to add...
    - old-fashioned rate-limiting for creation
        + would need to track per user
        + implementation CANNOT impact performance negatively
