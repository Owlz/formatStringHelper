formatStringTest: formatStringTest.c
	gcc -Wno-format-security -m32 -o formatStringTest formatStringTest.c
