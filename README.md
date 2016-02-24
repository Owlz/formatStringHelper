# formatStringExploiter
Helper script for working with format string bugs

# Overview
It's built to be both a python library and console application. For python, just import it.

This tool only supports i386 at the moment.

For quick start, just type 
```bash
$ make
$ ./formatStringExploiter.py formatStringTest
```

# Dependencies
You will need pwntools and prettytable

```bash
mkvirtualenv pwntools
pip install pwntools
pip install prettytable
```

# Examples
Easiest way to learn is to watch, right? Here is an example I've written on this:

* <https://bannsecurity.com/index.php/home/10-ctf-writeups/31-internetwache-ctf-2016-remote-printer>
