#!/usr/bin/env python

import os

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))

import sys
sys.path.insert(0, os.path.join(SCRIPTDIR,"..",".."))

from FormatString import FormatString
from pwn import *
import logging

def exec_fmt(s):
    sys.stdout.write("Execing " + s)
    sys.stdout.flush()
    p.sendline(s)
    out = p.recvuntil("myVar value is:").split("myVar value is:")[0]
    p.recvuntil("Input: ")
    sys.stdout.write("Returning " + out)
    sys.stdout.flush()
    return out


def get_myVar():
    p.sendline("blerg")
    p.recvuntil("myVar value is: ")
    ret = int(p.recvline(),16)
    p.recvuntil("Input: ")
    return ret

def startIt():
    global elf
    global p
    global fmtStr
    elf = ELF(os.path.join(SCRIPTDIR,fName))
    p = process(os.path.join(SCRIPTDIR,fName),bufSize=0xffff)
    fmtStr = FormatString(exec_fmt,elf=elf)


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

fName = "amd64_echoService"


def test_matching():
    startIt()
    assert u32(fmtStr[elf.symbols['myVar']]) == get_myVar()
    p.close()

def test_change_byte():
    startIt()
    fmtStr.write_b(elf.symbols['myVar']+3,0xbe)
    assert get_myVar() == 0xbeadbeef
    assert u32(fmtStr[elf.symbols['myVar']]) == get_myVar()
    p.close()

def test_change_word():
    startIt()
    fmtStr.write_w(elf.symbols['myVar'],0xf00d)
    assert get_myVar() == 0xdeadf00d
    assert u32(fmtStr[elf.symbols['myVar']]) == get_myVar()
    p.close()

def test_change_dword():
    startIt()
    fmtStr.write_d(elf.symbols['myVar'],0xcafebab3)
    assert get_myVar() == 0xcafebab3
    assert u32(fmtStr[elf.symbols['myVar']]) == get_myVar()
    p.close()

def test_change_null_byte():
    startIt()
    fmtStr.write_b(elf.symbols['myVar']+3,0)
    assert get_myVar() == 0xadbeef
    assert fmtStr.leak.p(elf.symbols['myVar']) == get_myVar()
    p.close()

def test_change_word():
    startIt()
    fmtStr.write_w(elf.symbols['myVar'],0)
    assert get_myVar() == 0xdead0000
    assert fmtStr.leak.p(elf.symbols['myVar']) == get_myVar()
    p.close()

def test_change_dword():
    startIt()
    fmtStr.write_d(elf.symbols['myVar'],0)
    assert get_myVar() == 0
    assert fmtStr.leak.p(elf.symbols['myVar']) == get_myVar()
    p.close()
