/* A disposable executable that imports dinput8, without opening a wheel device.
   Production ASI must refuse it; a separately built fixture ASI recognizes it. */
#define COBJMACROS
#include "fix.h"
#include <dinput.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

unsigned char abi_snapshot[176];
__declspec(dllexport) uintptr_t FixtureCtor(void *object, uintptr_t action, uintptr_t a, uintptr_t b, uintptr_t c);
uintptr_t FixtureBody(void *object, uintptr_t action, uintptr_t a, uintptr_t b, uintptr_t c) {
    (void)action; (void)a; (void)b; (void)c;
    return ((unsigned char *)object)[0x44];
}

int main(int argc, char **argv) {
    /* This triggers loader imports but never calls CreateDevice or sends effects. */
    IDirectInput8W *input = NULL;
    HRESULT hr = DirectInput8Create(GetModuleHandleW(NULL), DIRECTINPUT_VERSION,
                                   &IID_IDirectInput8W, (void **)&input, NULL);
    if (SUCCEEDED(hr) && input) IDirectInput8_Release(input);
    Sleep(100);
    HMODULE plugin = GetModuleHandleW(L"SnowRunnerFFBFix.asi");
    if (!plugin) { fprintf(stderr,"ASI was not automatically loaded\n"); return 1; }
    typedef void (*StatusFn)(FixStatus *);
    StatusFn get_status = (StatusFn)(uintptr_t)GetProcAddress(plugin,"GetFixStatus");
    if (!get_status) return 2;
    FixStatus before, after;
    get_status(&before);
    typedef void (*InitFn)(void);
    InitFn init = (InitFn)(uintptr_t)GetProcAddress(plugin,"InitializeASI");
    if (!init) return 5;
    init(); /* Repeated calls cannot install a second detour or re-arm a failure. */
    get_status(&after);
    if (after.armed != before.armed || after.applied != before.applied) return 6;
    unsigned char *obj = VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    if (!obj) return 3;
    memset(obj,0x61,4096);
    uintptr_t result = FixtureCtor(obj,0,0,0,0);
    get_status(&after);
    BOOL expect_active = argc == 2 && !strcmp(argv[1],"active");
    if (!!before.armed != expect_active || result != (expect_active ? 0 : 0x61) ||
        after.applied != (expect_active ? 1 : 0) || after.failed) {
        fprintf(stderr,"Unexpected state: armed=%ld result=%llu applied=%lld\n",before.armed,(unsigned long long)result,after.applied);
        return 4;
    }
    /* Give status worker time to record application. */
    Sleep(2200);
    VirtualFree(obj,0,MEM_RELEASE);
    printf("PASS automatic loader; armed=%ld applied=%lld\n",after.armed,after.applied);
    return 0;
}
