asm1:
	<+0>:	endbr32 
	<+4>:	push   ebp
	<+5>:	mov    ebp,esp
	<+7>:	cmp    DWORD PTR [ebp+0x8],0x6c8
	<+14>:	jg     0x11d6 <asm1+41>
	<+16>:	cmp    DWORD PTR [ebp+0x8],0x36e
	<+23>:	jne    0x11ce <asm1+33>
	<+25>:	mov    eax,DWORD PTR [ebp+0x8]
	<+28>:	add    eax,0x6
	<+31>:	jmp    0x11ed <asm1+64>
	<+33>:	mov    eax,DWORD PTR [ebp+0x8]
	<+36>:	sub    eax,0x6
	<+39>:	jmp    0x11ed <asm1+64>
	<+41>:	cmp    DWORD PTR [ebp+0x8],0xbef
	<+48>:	jne    0x11e7 <asm1+58>
	<+50>:	mov    eax,DWORD PTR [ebp+0x8]
	<+53>:	sub    eax,0x6
	<+56>:	jmp    0x11ed <asm1+64>
	<+58>:	mov    eax,DWORD PTR [ebp+0x8]
	<+61>:	add    eax,0x6
	<+64>:	pop    ebp
	<+65>:	ret    

