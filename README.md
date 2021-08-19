
# <img src="plugin.video.srf_ch_replay/icon.png" width="75" height="75" /> Unofficial SRF Replay (another official Kodi add-on) 

## Migration
This add-on has been migrated from [SRF Podcast Plugin](https://kodi.wiki/view/Add-on:SRF_Podcast_Plugin) [[source code](https://github.com/ambermoon/xbmc_plugin_video_srf_podcast_ch)] as its development seems to be on hold and unfortunately the add-on is not compatible with the newest Kodi version anymore. Thanks to all the previous developers who maintained the original add-on that I used and appreciated a lot.

## Add-on description
The add-on has been renamed to "Unofficial SRF Replay". It only supports the SRF channel and the only feature is to list and play all TV shows. All other channels and features from the original add-on have been refactored out. You might ask yourself 'Why?'. Well, never put avocado on a burger! Simple is always best!

Since the tag 2.0.0 the add-on is in the official [Kodi 19 (Matrix) repository](https://github.com/xbmc/repo-plugins/tree/matrix/plugin.video.srf_ch_replay) / [Kodi Add-on Page](https://kodi.tv/addons/matrix/plugin.video.srf_ch_replay).

## Add-on Usage
The add-on is self-explanatory but it can be used most efficiently in combination with favorites. When all the TV Shows are listed, just select your favorite show and open the Kodi context menu (press "c" on your keyboard) and select "Add to favorites".

![Select favorites](pictures/usage1.png)

The TV show just appears and the Kodi favorite menu and can be selected from there without going through the whole list every time.

![Select favorites](pictures/usage2.png)

Every time you select a TV show from your favorites only this show's content will be loaded. You will save click and loading time.

> *When the official API has been enabled then previously created favorites will not work anymore. Sorry for the inconvenience but the old ones need to be removed manually and then re-created.*

## Add-on Settings

### General
No explanation provided. You got so far, we are sure you already figured it out ;)

### Official API
Since tag 2.0.2 there is a new optional setting which is disabled by default.

![Official API](pictures/new_api_settings.png)

This new setting allows to connect to the official SRG SSR API. This API is documented and supported by SRG SSR and is more stable on the long run and comes with some advantages (like all SRG SSR TV channels are supported; so check the upcoming new versions you might find some new features :-|). If not enabled the add-on uses an undocumented and not publicly supported API and we keep it alive for some time but with an uncertain future. So be prepared.

In order to use the new API a consumer key and secret has to be claimed by each user. Therefore an account needs to be opened and some information need to be provided. Yes really, no way around it. So read the next section carefully.

#### Register
Open an account [at SRG SSR here](https://developer.srgssr.ch/user/register) and log in.

<kbd>![Register @ SRG SSR](pictures/new_api_register.png)</kbd>

Go to "My Apps" and press "ADD A NEW APP". Yep, the blue on.

 <kbd>![New API](pictures/new_api_register_add_app.png)</kbd>

Then put in
> kodi_addon_unofficial_srf_replay

> https[]()://kodi.tv/addons/matrix/plugin.video.srf_ch_replay
 
and chose
 * Hackdays
 
and press "Create App".

<kbd>![New APP](pictures/new_api_register_app.png)</kbd>
 
Your consumer key and secret have been created.
Now copy the consumer key and secret to Kodi add-on settings. 
 
Ready to go you are! ~Yoda
 

## Installation

### Kodi repository
Go to the add-ons menu in your installed Kodi and select "Install from repository". Search for the add-on (just type "srf") and hit "install".

### Manual
If you want the latest features after the branch has been tagged then you need to install the code manually.

Just zip the `plugin.video.srf_ch_replay` folder. Alternatively use the ant `build.xml` file and run the default `zip` target to build the zip file.

Go to the add-ons menu and select "Install from zip file". Follow the instructions and at the end select the zip file and install. The "SRF Replay" add-on will appear immediately in your add-ons menu. If you get and error that your usb stick can not be read just restart Kodi and try again.

