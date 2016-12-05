=======
Gotchas
=======

Hanging on Write
================
There are a few reasons for hanging on write. Check the following:

* Check your format string harness waiting on input.
* Check your ``badChars`` input to the FormatString class. Depending on how your program recieves input, it may have different characters to avoid.
* If you are using ``pwntools`` to communicate with the application, be sure to add ``buffer_fill_size=0xffff`` to the setup line, such as ``p = process("./a.out",buffer_fill_size=0xffff``.

On the last, there is currently a limitation in how ``pwntools`` handles recieving input where it will only recieve a maximum of 4096 characters. When writing large values, you will write up to 65535 characters, thus this argument is needed. At time of writing, this change is in a pull request and not yet in ``pwntools`` proper. If you are having issues, use my fork of ``pwntools`` as it has this change integrated. https://github.com/owlz/pwntools


Reading/Writing With No Control Buffer
======================================
One nice aspect of the initial version of this tool was that it supported reading and writing of values that already exist on the stack when we do not have a buffer that we control. This is high on the devlopment list, but for the moment it is not possible with this tool. This is only applicable if you do not have access to your source buffer.