# formatStringExploiter
Helper script for working with format string bugs

# New install process
formatStringExploiter is now on pypi. Simply setup a virtual environment (optional, but recommended), then `pip install formatStringExploiter`.

# NOTE
I'm reworking how this tool interacts to make it more in line with a scriptable solution. It's now beginning to be class based and has integrations with pwntools. Given a format string function, it will automatically discover where your control points are and allow for primitives to read memory.

Example

```python
from FormatString import FormatString
from pwn import *
import logging

logging.basicConfig(level=logging.WARN)
log = logging.getLogger()

elf = ELF("formatStringTest")

# Defining format string executor here
def exec_fmt(s):
    p = process("./formatStringTest",buffer_fill_size=0xffff)
    p.sendline(s)
    p.recvuntil("Input a format string: ")
    out = p.recvuntil("Logged in",drop=True)
    p.close()
    return out

# Create the class and self-discover the correct offsets
fmtStr = FormatString(exec_fmt,elf=elf)

# Leak some point in memory as a string
fmtStr[elf.symbols['secret']]
```

# Known Issues
Right now, there's a little problem (not really a bug) in the handling of using this tool in conjunction with pwntools to write a large value (or really any amount over 4096 chars). There is a pull request in right now to address this, so the fixing is coming but it will be a little before it's in the production release.

For now, a workaround would be to use the version that's in my repo (https://github.com/owlz/pwntools) as it has the patch applied. You will also need to add `buffer_fill_size = 0xffff` to your `process` or `remote` initialization lines. See the above example.

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
Easiest way to learn is to watch, right? Here are examples I've written on this:

* <https://bannsecurity.com/index.php/home/10-ctf-writeups/31-internetwache-ctf-2016-remote-printer>
* <https://bannsecurity.com/index.php/home/10-ctf-writeups/32-camp-ctf-2015-hacker-level>
