# DF-BAMM v0.1: The Graphicsenating
Button's Automated Mod Merger for Dwarf Fortress

What's here now:
* Graphics merging that works even on ridiculously modded raws.
* A friggin' awesome name.
 
What's coming soon:
* More/better options, so you can tell it what files you want ignored.
* The ability to write condensed, graphics-only raw files.
* Easy hooks for use by other utilities, cough LNP cough.

What's coming eventually:
* Merges of content as well as graphics.

Limitations:
* If you have two files with the same name, you're gonna have a bad time.
 
TO RUN
0. Have Python 3 installed.
1. Open /resources/run.config in a text editor.
2. Edit the properties named 'source', 'target' and 'output' as you like. 'Source' refers to the graphics set you want to apply, 'target' to the raws you want to apply them to, and 'output' to the output directory (which should be empty, it may overwrite the contents of the directory if it exists.)
3. Execute the file run_default.py .
 
NOTE TO DEVELOPERS
Sorry the documentation is crappy and some of the convenience functionality isn't there yet, I'm working on it.

Also sorry if my style sucks, I've looked up style things when I think to, but I'm completely self-taught in Python so my logic isn't always the most Pythonic.
