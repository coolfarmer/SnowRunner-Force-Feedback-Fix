/* Only the known constructor's entry is detoured. No wheel API, gain or filter. */
#include "fix.h"
#include "MinHook.h"
#include <stdio.h>
#include <string.h>

void *g_original;
static volatile LONG armed;
static volatile LONG64 applied, failed, skipped;

void ReadFixStatus(FixStatus *out) {
    out->armed = InterlockedCompareExchange(&armed, 0, 0);
    out->applied = InterlockedCompareExchange64(&applied, 0, 0);
    out->failed = InterlockedCompareExchange64(&failed, 0, 0);
    out->skipped = InterlockedCompareExchange64(&skipped, 0, 0);
}
void DisarmFix(void) { InterlockedExchange(&armed, 0); }

void InitializeFields(void *object) {
    DWORD error = GetLastError();
    if (!InterlockedCompareExchange(&armed, 0, 0)) {
        InterlockedIncrement64(&skipped);
    } else {
        uintptr_t p = (uintptr_t)object, target = p + 0x44;
        uint64_t zero[2] = {0, 0}, after[2] = {1, 1};
        MEMORY_BASIC_INFORMATION m;
        SIZE_T written = 0, read = 0;
        /* One whole committed/private/read-write region; never alter its protection.
           A failure permanently disarms this process. Other in-flight callbacks
           may finish. This does not repair illegal concurrent object destruction. */
        if (p && target > p && target + 16 > target &&
            VirtualQuery((void *)target, &m, sizeof(m)) == sizeof(m) &&
            m.State == MEM_COMMIT && m.Type == MEM_PRIVATE && m.Protect == PAGE_READWRITE &&
            target >= (uintptr_t)m.BaseAddress && target - (uintptr_t)m.BaseAddress <= m.RegionSize &&
            m.RegionSize - (target - (uintptr_t)m.BaseAddress) >= 16 &&
            WriteProcessMemory(GetCurrentProcess(), (void *)target, zero, 16, &written) && written == 16 &&
            ReadProcessMemory(GetCurrentProcess(), (void *)target, after, 16, &read) && read == 16 &&
            after[0] == 0 && after[1] == 0) {
            InterlockedIncrement64(&applied);
        } else {
            InterlockedIncrement64(&failed);
            DisarmFix();
        }
    }
    SetLastError(error);
}

BOOL ValidateGuards(void *base, size_t image_size, const CodeGuard *guards, size_t count) {
    if (!base || !guards || !count) return FALSE;
    for (size_t i = 0; i < count; ++i) {
        const CodeGuard *g = &guards[i];
        if (!g->size || g->rva >= image_size || g->size > image_size - g->rva) return FALSE;
        size_t done = 0;
        while (done < g->size) {
            unsigned char bytes[256];
            size_t n = g->size - done < sizeof(bytes) ? g->size - done : sizeof(bytes);
            SIZE_T read = 0;
            MEMORY_BASIC_INFORMATION m;
            void *p = (unsigned char *)base + g->rva + done;
            if (VirtualQuery(p, &m, sizeof(m)) != sizeof(m) || m.State != MEM_COMMIT ||
                (m.Protect & (PAGE_GUARD | PAGE_NOACCESS)) ||
                !(m.Protect & (PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) ||
                !ReadProcessMemory(GetCurrentProcess(), p, bytes, n, &read) || read != n ||
                memcmp(bytes, g->bytes + done, n) != 0) return FALSE;
            done += n;
        }
    }
    return TRUE;
}

BOOL InstallFix(void *base, size_t image_size, const CodeGuard *guards, size_t count,
                uint32_t constructor_rva, char *reason, size_t capacity) {
    BOOL covered = FALSE;
    for (size_t i = 0; i < count; ++i)
        if (guards[i].rva == constructor_rva && guards[i].size >= 16) covered = TRUE;
    if (!covered || !ValidateGuards(base, image_size, guards, count)) {
        snprintf(reason, capacity, "INACTIVE: loaded code mismatch (unpacking, version or another hook)");
        return FALSE;
    }
    MH_STATUS status = MH_Initialize();
    if (status != MH_OK) {
        snprintf(reason, capacity, "INACTIVE: MH_Initialize: %s", MH_StatusToString(status));
        return FALSE;
    }
    void *target = (unsigned char *)base + constructor_rva;
    status = MH_CreateHook(target, ConstructorThunk, &g_original);
    if (status == MH_OK) {
        /* Trampoline prepared, then pin this module before any thread can enter it.
           No live unloading; remove plugin only after exiting the game. */
        HMODULE pinned;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                              (const wchar_t *)(uintptr_t)&InitializeFields, &pinned)) {
            MH_RemoveHook(target);
            MH_Uninitialize();
            snprintf(reason, capacity, "INACTIVE: cannot pin plugin");
            return FALSE;
        }
        InterlockedExchange(&armed, 1);
        status = MH_EnableHook(target);
        if (status == MH_OK) {
            snprintf(reason, capacity, "ACTIVE: guarded constructor initialization");
            return TRUE;
        }
        DisarmFix();
        MH_RemoveHook(target);
    }
    MH_Uninitialize();
    snprintf(reason, capacity, "INACTIVE: detour installation: %s", MH_StatusToString(status));
    return FALSE;
}
