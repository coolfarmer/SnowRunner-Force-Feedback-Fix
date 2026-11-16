/* Windows x64 entry: preserve volatile registers, XMM0-5, flags, stack arguments
   and return address. Tail-jump to MinHook's trampoline; no guessed C signature. */
.text
.globl ConstructorThunk
.def ConstructorThunk; .scl 2; .type 32; .endef
.seh_proc ConstructorThunk
ConstructorThunk:
    leaq -200(%rsp), %rsp
    .seh_stackalloc 200
    .seh_endprologue
    movq %rax, 128(%rsp)
    movq %rcx, 136(%rsp)
    movq %rdx, 144(%rsp)
    movq %r8, 152(%rsp)
    movq %r9, 160(%rsp)
    movq %r10, 168(%rsp)
    movq %r11, 176(%rsp)
    pushfq
    popq %rax
    movq %rax, 184(%rsp)
    movdqu %xmm0, 32(%rsp)
    movdqu %xmm1, 48(%rsp)
    movdqu %xmm2, 64(%rsp)
    movdqu %xmm3, 80(%rsp)
    movdqu %xmm4, 96(%rsp)
    movdqu %xmm5, 112(%rsp)
    call InitializeFields
    movdqu 32(%rsp), %xmm0
    movdqu 48(%rsp), %xmm1
    movdqu 64(%rsp), %xmm2
    movdqu 80(%rsp), %xmm3
    movdqu 96(%rsp), %xmm4
    movdqu 112(%rsp), %xmm5
    pushq 184(%rsp)
    popfq
    movq 128(%rsp), %rax
    movq 136(%rsp), %rcx
    movq 144(%rsp), %rdx
    movq 152(%rsp), %r8
    movq 160(%rsp), %r9
    movq 168(%rsp), %r10
    movq 176(%rsp), %r11
    leaq 200(%rsp), %rsp
    jmp *g_original(%rip)
.seh_endproc
