#include "WarProgressionRules.h"

int64 WarProgression::XpForLevel(const int32 Level) { return 100 + int64(Level) * 150; }

bool WarProgression::Award(const FWarCharacterProgression& Current, const int32 Xp, const int32 Gold,
    FWarCharacterProgression& Next, FString& Error)
{
    Error.Reset();
    if (Xp < 0 || Gold < 0 || Current.Level < 1 || Current.Xp < 0 || Current.Xp >= XpForLevel(Current.Level)
        || Current.Gold < 0 || Current.Gold > MAX_int64 - Gold || Current.MaxHealth <= 0
        || Current.MaxMana <= 0 || Current.BaseStrength < 0)
    { Error = TEXT("Character reward or progression state is invalid."); return false; }
    auto Result = Current;
    Result.Xp += Xp; Result.Gold += Gold;
    // Normalized input and bounded reward sizes keep this loop below 6,000 iterations.
    while (Result.Xp >= XpForLevel(Result.Level))
    {
        if (Result.Level == MAX_int32 || Result.MaxHealth > MAX_int32 - 20
            || Result.MaxMana > MAX_int32 - 10 || Result.BaseStrength > MAX_int32 - 2)
        { Error = TEXT("Character stats exceed the supported range."); return false; }
        Result.Xp -= XpForLevel(Result.Level);
        ++Result.Level; Result.MaxHealth += 20; Result.MaxMana += 10; Result.BaseStrength += 2;
    }
    Next = Result; return true;
}
