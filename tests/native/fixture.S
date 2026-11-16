.text
.globl FixtureCtor
.def FixtureCtor; .scl 2; .type 32; .endef
FixtureCtor:
    /* Exact first two instructions of the captured real constructor. */
    movq %rdx, 16(%rsp)
    movq %rcx, 8(%rsp)
    jmp FixtureBody
    .fill 32, 1, 0x90

.globl AbiTarget
.def AbiTarget; .scl 2; .type 32; .endef
AbiTarget:
    movq %rdx, 16(%rsp)
    movq %rcx, 8(%rsp)
    movq %rax, abi_snapshot+0(%rip)
    movq %rcx, abi_snapshot+8(%rip)
    movq %rdx, abi_snapshot+16(%rip)
    movq %r8, abi_snapshot+24(%rip)
    movq %r9, abi_snapshot+32(%rip)
    movq %r10, abi_snapshot+40(%rip)
    movq %r11, abi_snapshot+48(%rip)
    pushfq
    popq %rax
    movq %rax, abi_snapshot+56(%rip)
    movdqu %xmm0, abi_snapshot+64(%rip)
    movdqu %xmm1, abi_snapshot+80(%rip)
    movdqu %xmm2, abi_snapshot+96(%rip)
    movdqu %xmm3, abi_snapshot+112(%rip)
    movdqu %xmm4, abi_snapshot+128(%rip)
    movdqu %xmm5, abi_snapshot+144(%rip)
    movq 40(%rsp), %rax
    movq %rax, abi_snapshot+160(%rip)
    movq 48(%rsp), %rax
    movq %rax, abi_snapshot+168(%rip)
    movq $12345, %rax
    ret

.globl AbiInvoke
.def AbiInvoke; .scl 2; .type 32; .endef
.seh_proc AbiInvoke
AbiInvoke:
    subq $56, %rsp
    .seh_stackalloc 56
    .seh_endprologue
    movq $111, 32(%rsp)
    movq $222, 40(%rsp)
    movq $123, %rax
    movq $234, %rdx
    movq $345, %r8
    movq $456, %r9
    movq $567, %r10
    movq $678, %r11
    pcmpeqb %xmm0, %xmm0
    movdqa %xmm0, %xmm1
    psrlq $1, %xmm1
    movdqa %xmm1, %xmm2
    psrlq $1, %xmm2
    movdqa %xmm2, %xmm3
    psrlq $1, %xmm3
    movdqa %xmm3, %xmm4
    psrlq $1, %xmm4
    movdqa %xmm4, %xmm5
    psrlq $1, %xmm5
    cmpq %rax, %rax
    stc
    call AbiTarget
    addq $56, %rsp
    ret
.seh_endproc
