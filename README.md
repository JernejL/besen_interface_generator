# besen_interface_generator
besen integration interface generator based on rtti json builder

This python script loads pascal files and generates wrapper interace units to work with those classes from besen javascript engine.

Instructions:
Rename settings_example.json to settings.json
set paths to things like rtticonverter ( https://github.com/JernejL/pascal_rtti_json ), class files and lists to desired output.
rtticonverter will tell you which functions to implement to handle JS & native tye conversion ( TBTypeconvert )

A fully working example will be provided later.
