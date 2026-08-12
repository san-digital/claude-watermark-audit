	.build_version macos, 26, 0	sdk_version 26, 5
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main                           ; -- Begin function main
	.p2align	2
_main:                                  ; @main
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #64
	stp	x22, x21, [sp, #16]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #32]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #48]             ; 16-byte Folded Spill
	add	x29, sp, #48
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	cmp	w0, #1
	b.le	LBB0_2
; %bb.1:
	ldr	x0, [x1, #8]
	bl	_atoi
	mov	x19, x0
	cmp	w19, #1
	b.ge	LBB0_3
	b	LBB0_5
LBB0_2:
	mov	w19, #20                        ; =0x14
	cmp	w19, #1
	b.lt	LBB0_5
LBB0_3:
	mov	w20, #0                         ; =0x0
Lloh0:
	adrp	x21, l_.str@PAGE
Lloh1:
	add	x21, x21, l_.str@PAGEOFF
LBB0_4:                                 ; =>This Inner Loop Header: Depth=1
	mov	x0, x20
	bl	_fib
                                        ; kill: def $w0 killed $w0 def $x0
	stp	x20, x0, [sp]
	mov	x0, x21
	bl	_printf
	add	w20, w20, #1
	cmp	w19, w20
	b.ne	LBB0_4
LBB0_5:
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp, #48]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #32]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #16]             ; 16-byte Folded Reload
	add	sp, sp, #64
	ret
	.loh AdrpAdd	Lloh0, Lloh1
	.cfi_endproc
                                        ; -- End function
	.p2align	2                               ; -- Begin function fib
_fib:                                   ; @fib
	.cfi_startproc
; %bb.0:
	stp	x20, x19, [sp, #-32]!           ; 16-byte Folded Spill
	stp	x29, x30, [sp, #16]             ; 16-byte Folded Spill
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	mov	w19, #0                         ; =0x0
	subs	w20, w0, #2
	b.lt	LBB1_2
LBB1_1:                                 ; =>This Inner Loop Header: Depth=1
	sub	w0, w0, #1
	bl	_fib
	add	w19, w19, w0
	mov	x0, x20
	subs	w20, w0, #2
	b.ge	LBB1_1
LBB1_2:
	add	w0, w0, w19
	ldp	x29, x30, [sp, #16]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp], #32             ; 16-byte Folded Reload
	ret
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__cstring,cstring_literals
l_.str:                                 ; @.str
	.asciz	"fib(%d) = %d\n"

.subsections_via_symbols
