# INSTALL
On hassio host navigate to custom_component folder

```
git clone https://github.com/brianbola90/home-assistant-climote.git
```
Add the confgureation below and restart your instance


# home-assistant-climote
Climote Climate Platform for home-assistant

Climote is mobile text based remote heating control system. It causes delay in submitting and receiving updates. 
Refresh interval defines how often the update should be pulled from Climote, but bear in mind that putting 2h would mean over 4000 updates over a year. Might be excessive. 
```
climate:
  - platform: climote
    username: <email address>
    password: <password>
    id: <climote device id>
    refresh_interval: <integer for hours interval> 
```

To be done:

- Fix bug with Tempurature setting
