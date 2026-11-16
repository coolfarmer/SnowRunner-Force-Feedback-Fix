#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stddef.h>

typedef struct { uint32_t rva; size_t size; const unsigned char *bytes; } CodeGuard;
typedef struct {
    LONG armed;
    LONG64 applied, failed, skipped;
} FixStatus;

extern void *g_original;
void ConstructorThunk(void);
void InitializeFields(void *object);
void ReadFixStatus(FixStatus *out);
void DisarmFix(void);
BOOL ValidateGuards(void *base, size_t image_size, const CodeGuard *guards, size_t count);
BOOL InstallFix(void *base, size_t image_size, const CodeGuard *guards, size_t count,
                uint32_t constructor_rva, char *reason, size_t capacity);
BOOL Sha256File(const wchar_t *path, char out[65]);
