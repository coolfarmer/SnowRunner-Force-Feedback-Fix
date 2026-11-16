#include "fix.h"
#include "profile.h"
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static HMODULE self;
static volatile LONG started;
static wchar_t folder[32768], log_path[32768];
static char reason[256] = "INACTIVE: InitializeASI not called";

__declspec(dllexport) void GetFixStatus(FixStatus *out) { if (out) ReadFixStatus(out); }

static void WriteStatus(void) {
    FixStatus s;
    ReadFixStatus(&s);
    char text[1024];
    int length = snprintf(text, sizeof(text),
        "SnowRunnerFFBFix 0.2.0 experimental\r\nprofile=%s\r\npid=%lu\r\n%s\r\n"
        "armed=%ld\r\napplied=%lld\r\nfailed=%lld\r\nskipped=%lld\r\n"
        "Physical validation of this native plugin: pending\r\n",
        PROFILE_NAME, GetCurrentProcessId(), s.failed ? "DISARMED: memory initialization failed" : reason,
        s.armed, s.applied, s.failed, s.skipped);
    HANDLE file = CreateFileW(log_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_DELETE,
                              NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(file, text, (DWORD)length, &written, NULL);
        CloseHandle(file);
    }
    OutputDebugStringA(text);
}

static DWORD WINAPI StatusWorker(void *unused) {
    (void)unused;
    FixStatus previous = {-1, -1, -1, -1};
    for (;;) {
        FixStatus current;
        ReadFixStatus(&current);
        if (current.armed != previous.armed || current.applied != previous.applied ||
            current.failed != previous.failed || current.skipped != previous.skipped) {
            WriteStatus(); previous = current;
        }
        Sleep(2000);
    }
}

__declspec(dllexport) void InitializeASI(void) {
    DWORD error = GetLastError();
    if (InterlockedCompareExchange(&started, 1, 0)) { SetLastError(error); return; }
    DWORD n = GetModuleFileNameW(self, folder, 32768);
    if (!n || n >= 32768) goto done;
    wchar_t *slash = wcsrchr(folder, L'\\');
    if (!slash) goto done;
    slash[1] = 0;
    if (wcslen(folder) > 32000) goto done;
    swprintf(log_path, 32768, L"%lsSnowRunnerFFBFix.log", folder);
    wchar_t path[32768];
    swprintf(path, 32768, L"%lsSnowRunnerFFBFix.disabled", folder);
    if (GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES) {
        strcpy(reason, "DISABLED: marker file exists"); goto report;
    }
    n = GetModuleFileNameW(NULL, path, 32768);
    char hash[65];
    if (!n || n >= 32768 || !Sha256File(path, hash) || strcmp(hash, GAME_SHA256)) {
        strcpy(reason, "INACTIVE: unknown game executable SHA256; no hook installed"); goto report;
    }
    /* Shared game-side producer: no wheel SDK dependency. The executable hash
       above and all loaded-code guards below remain mandatory. */
    unsigned char *base = (unsigned char *)GetModuleHandleW(NULL);
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
    IMAGE_NT_HEADERS64 *nt = (IMAGE_NT_HEADERS64 *)(base + dos->e_lfanew);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || nt->Signature != IMAGE_NT_SIGNATURE ||
        nt->FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64) {
        strcpy(reason, "INACTIVE: unexpected PE image"); goto report;
    }
    if (InstallFix(base, nt->OptionalHeader.SizeOfImage, PROFILE_GUARDS,
                   sizeof(PROFILE_GUARDS)/sizeof(PROFILE_GUARDS[0]), CONSTRUCTOR_RVA,
                   reason, sizeof(reason))) {
        HANDLE thread = CreateThread(NULL, 0, StatusWorker, NULL, CREATE_SUSPENDED, NULL);
        if (thread) {
            /* Write initial state before the worker can write to the same file. */
            WriteStatus();
            ResumeThread(thread); CloseHandle(thread);
            goto done;
        }
        /* Correction is active even if status polling is unavailable. */
        strcat(reason, "; status worker unavailable");
    }
report:
    WriteStatus();
done:
    SetLastError(error);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD why, void *reserved) {
    (void)reserved;
    if (why == DLL_PROCESS_ATTACH) {
        self = instance;
        DisableThreadLibraryCalls(instance);
    }
    /* Never patch, hash, create threads or wait under the loader lock. */
    return TRUE;
}
