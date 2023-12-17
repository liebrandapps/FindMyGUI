
Disclaimer

Use this application at your own risk! Use this application with care especially to avoid blocking of your Apple Id. 
Read the Safety part of this file to understand the unencrypted transmission of data. No guarantee that this application
works at all times and is fit for a certain purpose.


Configuration

For all configuration settings default values are defined in main.py. In case you need to configure something different, 
you need to create an ini file at the project root level. The file is called 'findMyGUI.ini' and has the standard
ini file format. 

In case your anisette server is not on the same host as this server or does not run on port 6969, you need to specify 
the values

[general]
anisetteHost=http://your ip here
anisettePort=your port number here

In case you want to configure the Apple Id in the configuration file:

[appleId]
appleId=Your Apple Id
password=Your password
trustedDevice=True -> to be prompted on your Apple Device, False -> 2nd factor as SMS
        

Safety

NEVER RUN THIS SERVER IN AN UNSAFE ENVIRONMENT:

Retrieval of the location data requires the use of an Apple Id and its password. Depending on how the ID is set up, you
may be required to enter a 2nd factor. You can configure your Apple Id credentials in the ini file on the server. If you 
decide to not do this (which is perfectly valid), you are asked upon retrieval of the location data in the browser. 

>>> Be aware that the data is transferred without encryption. <<<

2nd Factor (never reaching you)

Most Apple Ids are configured to use a 2nd factor. The web front end prompts you to enter the 2nd factor value received 
in the browser. By default, the app is configured to request the 2nd factor via SMS. If your Apple Id is configured to
receive those codes via your devices then sms may not work (and the code never arrives). If this is the case try to set
'trustedDevice' in section [appleId] of the 'findMyGUI.ini' to True. 