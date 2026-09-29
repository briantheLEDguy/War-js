#pragma once
#include "CoreMinimal.h"

class AActor;
struct FWarCombatNotice
{
    FName Kind;
    FString Label;
    float Amount = 0;
    double Expires = 0;
};

namespace WarCombatFeedback
{
    AEGISWAR_API bool Valid(FName Kind, float Amount);
    AEGISWAR_API bool Append(TArray<FWarCombatNotice>& Notices, uint32& LastSerial, uint32 Serial,
        FName Kind, const FString& Label, float Amount, double Now);
    /** Only the authoritative effect path publishes outcomes to involved players. */
    AEGISWAR_API void Emit(AActor* Source, AActor* Target, FName Kind, float Amount);
}
